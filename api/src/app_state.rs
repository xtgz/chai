use std::sync::Arc;
use tokio_postgres::Client;

pub struct AppState {
    pub client: Arc<Client>,
    pub tables: Arc<Vec<String>>,
}
