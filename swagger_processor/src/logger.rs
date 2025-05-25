use pyo3::prelude::*;
use std::sync::Arc;

// Thread-safe logger wrapper
#[derive(Clone)]
pub struct ThreadSafeLogger {
    logger: Arc<Py<PyAny>>,
}

impl ThreadSafeLogger {
    pub fn new(logger: Py<PyAny>) -> Self {
        Self {
            logger: Arc::new(logger),
        }
    }

    fn log(&self, py: Python, level: &str, message: &str) {
        // Silently ignore logging errors to avoid breaking main logic
        let _ = self.logger.bind(py).call_method1(level, (message,));
    }

    pub fn info(&self, py: Python, message: &str) {
        self.log(py, "info", message);
    }

    pub fn debug(&self, py: Python, message: &str) {
        self.log(py, "debug", message);
    }

    pub fn error(&self, py: Python, message: &str) {
        self.log(py, "error", message);
    }
}
