use env_logger::Env;

pub fn setup_logger() {
    env_logger::init_from_env(Env::default().default_filter_or("info"));
}

pub struct Logger;

impl Logger {
    pub fn default() -> actix_web::middleware::Logger {
        actix_web::middleware::Logger::new("%a '%r' %s %b '%{Referer}i' '%{User-Agent}i' %T")
    }
}
