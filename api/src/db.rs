use std::sync::Arc;
use tokio_postgres::{Client, NoTls};

pub async fn create_db_client(database_url: &str) -> Arc<Client> {
    let (client, connection) = tokio_postgres::connect(database_url, NoTls)
        .await
        .expect("Failed to connect to PostgreSQL");

    tokio::spawn(async move {
        if let Err(e) = connection.await {
            log::error!("Database connection error: {}", e);
        }
    });

    Arc::new(client)
}

pub async fn get_tables(client: &Arc<Client>) -> Vec<String> {
    let rows = client
        .query(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
            &[],
        )
        .await
        .expect("Failed to fetch tables");

    rows.into_iter()
        .map(|row| row.get::<_, String>("table_name"))
        .collect()
}
