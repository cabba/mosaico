use mosaicod_ext::arrow::testing::dummy_batch;
use mosaicod_repo as repo;
use tests::{common, actions};

fn valid_key(key: &uuid::Uuid) -> bool {
    !key.is_nil() && !key.is_max()
}

#[sqlx::test(migrator = "mosaicod_repo::testing::MIGRATOR")]
fn upload_data(pool: sqlx::Pool<repo::Database>) -> sqlx::Result<()> {
    let port = common::random_port();
    let server = common::Server::new(common::HOST, port, pool).await;
    let mut client = common::Client::new(common::HOST, port).await;

    let seq_name = "test_sequence";
    let seq_key = actions::sequence_create(&mut client, seq_name, None).await;
    assert!(valid_key(&seq_key));

    let topic_name = format!("{}/my_topic", seq_name);
    let topic_key = actions::topic_create(&mut client, &seq_key, &topic_name, None).await;
    assert!(valid_key(&topic_key));

    let batch = dummy_batch();

    // Upload data
    actions::upload_data(&mut client, &topic_key, &topic_name, batch).await;

    server.shutdown().await;
    Ok(())
}
