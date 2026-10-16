"""
LeRobot dataset reader.

This module reads the `data/` folder of a LeRobot v3.0 dataset with `pyarrow`, one episode at a time.

All the data parquet files are opened as a single `pyarrow` dataset. Each file holds several
episodes, stored contiguously, and LeRobot writes one parquet row group per episode: the rows of
an episode are selected with a filter on the `episode_index` column, and the row-group statistics
let `pyarrow` skip the other episodes without reading them.

The timeseries (every data column except `timestamp` and the images) are rearranged into a single
struct, without copying them: the Mosaico server rejects field names containing `.`, so dotted
column names are nested (`observation.state` becomes the field `state` of the struct `observation`).

Each image column (an image embedded in the data files, as a struct of the image file content
`bytes` and its file name `path`) is converted into the fields of the `CompressedImage` ontology,
without copying nor decoding the images.

The batches are cut and merged so that each one is as large as possible within the maximum batch
size accepted by the server.
"""

from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.ipc as pa_ipc

from mosaicolabs import CompressedImage, Header
from mosaicolabs.models.core import Message

from .helpers import _max_rows_within, _to_timestamp_ns
from .metadata import _TIMESTAMP_COLUMN_NAME, LeRobotDatasetMeta

DEFAULT_BATCH_SIZE = 131_072
"""The default maximum number of rows of a batch (the `pyarrow` default)."""

IMAGE_BATCH_SIZE = 100
"""The maximum number of rows read at a time from an image column, to bound the memory used."""

_DATA_DIR = "data"
_EPISODE_INDEX_COLUMN = "episode_index"
_NESTED_NAME_SEP = "."
_NOT_FOUND = -1


def _timeseries_fields_to_msco_schema(fields: List[pa.Field]) -> pa.Schema:
    """
    Builds the Mosaico compatible schema of the timeseries from their parquet fields.

    The Mosaico server rejects field names containing `.`, so the fields with a dotted name are
    nested into structs, at any depth: the fields `action`, `observation.state` and
    `observation.force` become the field `action` and the struct `observation` holding `state`
    and `force`. A struct takes the position of its first field.

    Raises:
        ValueError: If a name is both a field and a struct (e.g. `observation` and `observation.state`).
    """
    tree: Dict[str, Any] = {}
    for field in fields:
        *parents, leaf = field.name.split(_NESTED_NAME_SEP)
        node = tree
        for depth, parent in enumerate(parents, start=1):
            node = node.setdefault(parent, {})
            if not isinstance(node, dict):
                name = _NESTED_NAME_SEP.join(parents[:depth])
                raise ValueError(f"'{name}' cannot be both a column and a struct.")
        if leaf in node:
            raise ValueError(f"'{field.name}' cannot be both a column and a struct.")
        node[leaf] = pa.field(leaf, field.type, field.nullable)

    def to_struct(node: Dict[str, Any]) -> pa.StructType:
        return pa.struct(
            [
                pa.field(name, to_struct(child)) if isinstance(child, dict) else child
                for name, child in node.items()
            ]
        )

    return pa.schema(list(to_struct(tree)))


def _adapt_timeseries_rb_to_schema(
    batch: pa.RecordBatch, schema: pa.Schema
) -> pa.RecordBatch:
    """
    Rearranges the columns of `batch` into the fields of `schema`, as grouped by
    `_timeseries_fields_to_msco_schema`.

    The column arrays are reused as they are: no data is copied.
    """

    def build(field: pa.Field, name: str) -> pa.Array:
        # A field is either a column of the batch, or the struct of the columns `name.*`
        if batch.schema.get_field_index(name) != _NOT_FOUND:
            return batch.column(name)
        return pa.StructArray.from_arrays(
            [
                build(child, f"{name}{_NESTED_NAME_SEP}{child.name}")
                for child in field.type
            ],
            fields=list(field.type),
        )

    return pa.RecordBatch.from_arrays(
        [build(field, field.name) for field in schema], schema=schema
    )


def _adapt_image_rb_to_schema(
    image: pa.StructArray, schema: pa.Schema
) -> pa.RecordBatch:
    """
    Converts an image column into the fields of `schema`, the `CompressedImage` ontology.

    The image column is a struct of the image file content (`bytes`) and of the name of the file
    LeRobot wrote it to (`path`): `bytes` becomes `data` as it is (the image is not copied nor
    decoded), the lowercase extension of `path` becomes `format`, and `header` is null.
    """

    def fill_none(array: pa.Array) -> pa.Array:
        return pc.fill_null(array, pa.scalar(b"", type=pa.binary()))

    def to_image_format(array: pa.Array) -> pa.Array:
        ext = pc.extract_regex(array, r"\.(?P<ext>[^./\\]+)$").field("ext")
        ext = pc.utf8_lower(ext)

        return ext

    column_names_transformation_mapper = {
        "bytes": fill_none,
        "path": to_image_format,
    }

    # flatten() applies the struct's own nulls (frames without an image) to its children
    children = dict(zip(image.type.names, image.flatten()))

    def apply_transformation(col_name: str) -> pa.Array:

        transformation = column_names_transformation_mapper[col_name]
        return transformation(children[col_name])

    header = pa.nulls(len(image), Header.__msco_pyarrow_struct__)

    trans_img = [apply_transformation(col_name) for col_name in image.type.names]

    return pa.RecordBatch.from_arrays(
        [header, *trans_img],
        schema=schema,
    )


class LeRobotReader:
    """
    Reads the data parquet files of a LeRobot v3.0 dataset, one episode at a time.

    Example:
        ```python
        meta = LeRobotDatasetMeta.load(root)
        reader = LeRobotReader(root, meta, client.max_batch_size_bytes)
        for batch in reader.iter_timeseries_batches(0):
            ...
        for camera_column_name in reader.get_cameras_column_names():
            for batch in reader.iter_image_batches(0, camera_column_name):
                ...
        ```
    """

    def __init__(self, root: Path, meta: LeRobotDatasetMeta, max_batch_size_bytes: int):
        """
        Args:
            root (Path): The root folder of the dataset.
            meta (LeRobotDatasetMeta): The dataset metadata, loaded from `root`.
            max_batch_size_bytes (int): The maximum size of the batches sent to the server
                (see `MosaicoClient.max_batch_size_bytes`).

        Raises:
            FileNotFoundError: If `data/` is missing or holds no parquet file.
            ValueError: If the data files have no `timestamp` column, or the timeseries columns
                cannot be nested (a name is both a column and a struct).
        """
        data_dir = Path(root) / _DATA_DIR
        if not data_dir.is_dir():
            raise FileNotFoundError(f"'{data_dir}' is not a directory.")

        data_files = sorted(data_dir.rglob("*.parquet"))
        if not data_files:
            raise FileNotFoundError(f"No data parquet file found in '{data_dir}'.")

        self._meta = meta
        self._max_batch_size_bytes = max_batch_size_bytes
        self._dataset: ds.Dataset = ds.dataset(
            [str(data_file) for data_file in data_files], format="parquet"
        )

        schema = self._dataset.schema
        if _TIMESTAMP_COLUMN_NAME not in schema.names:
            raise ValueError(
                f"The data files have no '{_TIMESTAMP_COLUMN_NAME}' column."
            )

        self._image_column_names: List[str] = [
            key for key, feature in meta.features.items() if feature.is_image
        ]
        # The order of the columns is the order of the timeseries struct fields
        self._timeseries_column_names: List[str] = [
            key for key, feature in meta.features.items() if feature.is_timeserie
        ]

        self._timeseries_schema: pa.Schema = _timeseries_fields_to_msco_schema(
            [schema.field(name) for name in self._timeseries_column_names]
        )

    def _iter_episode_batches(
        self,
        episode_index: int,
        columns: Optional[List[str]] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> Iterator[pa.RecordBatch]:
        """
        Reads the rows of an episode, in file order, as record batches.

        Only the row groups holding the episode are read. The number of rows of the episode is
        checked against its `meta/episodes` row before any batch is yielded.

        Args:
            episode_index (int): The episode index.
            columns (Optional[List[str]]): The columns to read (all of them if `None`).
            batch_size (int): The maximum number of rows of each batch. Batches can be smaller,
                as they never span more than one row group.

        Yields:
            pa.RecordBatch: The episode rows, with the requested columns.

        Raises:
            ValueError: If the episode is not defined in `meta/episodes`, or its number of
                rows in the data files differs from its `length`.
        """
        episode = self._meta.episodes.get(episode_index)
        if episode is None:
            raise ValueError(
                f"Episode {episode_index} is not defined in 'meta/episodes'."
            )

        episode_filter = ds.field(_EPISODE_INDEX_COLUMN) == episode_index

        # Counted from the row-group statistics when a row group holds a single episode
        num_rows = self._dataset.count_rows(filter=episode_filter)
        if num_rows != episode.length:
            raise ValueError(
                f"Episode {episode_index} has {num_rows} rows in '{_DATA_DIR}/', "
                f"but its length in 'meta/episodes' is {episode.length}."
            )

        batches = self._dataset.to_batches(
            columns=columns, filter=episode_filter, batch_size=batch_size
        )

        for batch in batches:
            if batch.num_rows > 0:
                yield batch

    def _fit_batch(
        self, batch: pa.RecordBatch
    ) -> Tuple[List[pa.RecordBatch], pa.RecordBatch]:
        """
        Cuts `batch` into batches as large as possible within `max_batch_size_bytes`.

        Returns:
            Tuple[List[pa.RecordBatch], pa.RecordBatch]: The full batches, and the rows left
                over, which fit within `max_batch_size_bytes` and can be sent together with the
                next rows. Both are slices of `batch`: no data is copied.

        Raises:
            ValueError: If a single row exceeds `max_batch_size_bytes`.
        """
        max_size = self._max_batch_size_bytes
        full_rbs: List[pa.RecordBatch] = []
        while pa_ipc.get_record_batch_size(batch) > max_size:
            rows = _max_rows_within(batch, max_size)
            if rows == 0:
                row_size = pa_ipc.get_record_batch_size(batch.slice(0, 1))
                raise ValueError(
                    f"Single row size {row_size} bytes > {max_size} bytes maximum allowed batch size."
                )

            full_rbs.append(batch.slice(offset=0, length=rows))
            batch = batch.slice(offset=rows)
        return full_rbs, batch

    # Public API functions

    @property
    def timeseries_struct(self) -> pa.StructType:
        """
        The struct of the timeseries: every data column except `timestamp` and the images, with
        dotted names nested. It is the ontology schema of the timeseries topic (e.g. for
        `make_unmodeled_ontology_class`).
        """
        return pa.struct(self._timeseries_schema)

    def get_cameras_column_names(self) -> List[str]:
        """
        Returns the names of the image columns of the data files (the features of type `image`),
        as accepted by `iter_image_batches`.

        Returns:
            List[str]: The image column names (e.g. `observation.images.front`).
        """
        return list(self._image_column_names)

    def iter_timeseries_batches(self, episode_index: int) -> Iterator[pa.RecordBatch]:
        """
        Reads the timeseries of an episode, as the record batches sent to the server.

        Each batch holds the `timestamp_ns` column (the `int64` nanoseconds since the episode
        start, from `timestamp`), followed by the fields of `timeseries_struct`. The batches are
        as large as possible within `max_batch_size_bytes`: only the last one of the episode can
        be smaller. Only the `timestamp` and timeseries columns are read: the images are never
        loaded.

        Args:
            episode_index (int): The episode index.

        Yields:
            pa.RecordBatch: The timeseries rows, with the `timestamp_ns` column first.

        Raises:
            ValueError: If a timeseries column collides with the `timestamp_ns` envelope column,
                the episode is not defined in `meta/episodes`, its number of rows in the data
                files differs from its `length`, or a single row exceeds `max_batch_size_bytes`.
        """
        all_columns = [_TIMESTAMP_COLUMN_NAME, *self._timeseries_column_names]

        # The wire schema: the `timestamp_ns` envelope column + timeseries schema fields
        ts_timeseries_schema: pa.Schema = Message._get_schema(
            pa.struct(list(self._timeseries_schema))
        )

        # The rows left over by the previous batch, sent together with the next rows
        pending_rb: Optional[pa.RecordBatch] = None

        for batch in self._iter_episode_batches(episode_index, all_columns):
            timestamp_array = _to_timestamp_ns(batch.column(_TIMESTAMP_COLUMN_NAME))
            timeseries_rb = _adapt_timeseries_rb_to_schema(
                batch.select(self._timeseries_column_names), self._timeseries_schema
            )

            merged_rb = pa.RecordBatch.from_arrays(
                [timestamp_array, *timeseries_rb.columns],
                schema=ts_timeseries_schema,
            )

            if pending_rb is not None:
                # Copies the rows: only when the episode is read in more than one batch
                merged_rb = pa.concat_batches([pending_rb, merged_rb])

            full_rbs, pending_rb = self._fit_batch(merged_rb)
            yield from full_rbs

        if pending_rb is not None:
            yield pending_rb

    def iter_image_batches(
        self, episode_index: int, camera_column_name: str
    ) -> Iterator[pa.RecordBatch]:
        """
        Reads the images of a camera in an episode, as the record batches sent to the server.

        Each batch holds the `timestamp_ns` column (the `int64` nanoseconds since the episode
        start, from `timestamp`), followed by the fields of the `CompressedImage` ontology:
        `header` (null), `data` (the image file content) and `format` (the lowercase extension of
        the image file name). The batches are as large as possible within
        `max_batch_size_bytes`: only the last one of the episode can be smaller. Only the
        `timestamp` and `camera_column_name` columns are read, `IMAGE_BATCH_SIZE` rows at a time.

        Args:
            episode_index (int): The episode index.
            camera_column_name (str): The image column to read (see `get_cameras_column_names`).

        Yields:
            pa.RecordBatch: The image rows, with the `timestamp_ns` column first.

        Raises:
            ValueError: If `camera_column_name` is not an image column, the episode is not
                defined in `meta/episodes`, its number of rows in the data files differs from
                its `length`, or a single row exceeds `max_batch_size_bytes`.
        """

        if camera_column_name not in self._image_column_names:
            raise ValueError(
                f"Requested camera column name {camera_column_name} is not contained among batch columns. "
                f"Available camera column names are: {[c_name for c_name in self._image_column_names]}"
            )

        # The wire schema: the `timestamp_ns` envelope column, then the image struct fields
        ts_image_schema: pa.Schema = Message._get_schema(CompressedImage)

        all_columns = [_TIMESTAMP_COLUMN_NAME, camera_column_name]

        # The rows left over by the previous batch, sent together with the next rows
        pending_rb: Optional[pa.RecordBatch] = None

        for batch in self._iter_episode_batches(
            episode_index, all_columns, IMAGE_BATCH_SIZE
        ):
            timestamp_array = _to_timestamp_ns(batch.column(_TIMESTAMP_COLUMN_NAME))
            image_rb = _adapt_image_rb_to_schema(
                batch.column(camera_column_name),
                pa.schema(list(CompressedImage.__msco_pyarrow_struct__)),
            )

            merged_rb = pa.RecordBatch.from_arrays(
                [timestamp_array, *image_rb.columns],
                schema=ts_image_schema,
            )

            if pending_rb is not None:
                # Copies the rows: only when the episode is read in more than one batch
                merged_rb = pa.concat_batches([pending_rb, merged_rb])

            full_rbs, pending_rb = self._fit_batch(merged_rb)
            yield from full_rbs

        if pending_rb is not None:
            yield pending_rb
