use pyo3::prelude::*;
use pyo3::types::{PyModule, PyString, PyType};
mod logger;
mod processor;
mod types;
mod utils;

use processor::APIDefinitionProcessor;
use types::APIDefinitionError;

/// PyO3 module definition
#[pymodule]
fn swagger_processor(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<APIDefinitionProcessor>()?;
    m.add(
        "APIDefinitionError",
        m.py().get_type::<APIDefinitionError>(),
    )?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn setup_test_env() {
        pyo3::prepare_freethreaded_python();
    }

    #[test]
    fn test_module_initialization() {
        setup_test_env();
        Python::with_gil(|py| {
            let module = PyModule::new(py, "swagger_processor").unwrap();
            let result = swagger_processor(&module);
            assert!(result.is_ok());
        });
    }

    #[test]
    fn test_class_registration() {
        setup_test_env();
        Python::with_gil(|py| {
            let module = PyModule::new(py, "swagger_processor").unwrap();
            swagger_processor(&module).unwrap();

            // Test APIDefinitionProcessor class registration
            let processor_class = module.getattr("APIDefinitionProcessor").unwrap();
            assert!(processor_class.is_instance_of::<PyType>());

            // Test APIDefinitionError type registration
            let error_type = module.getattr("APIDefinitionError").unwrap();
            assert!(error_type.is_instance_of::<PyType>());
        });
    }

    #[test]
    fn test_processor_instantiation() {
        setup_test_env();
        Python::with_gil(|py| {
            let module = PyModule::new(py, "swagger_processor").unwrap();
            swagger_processor(&module).unwrap();

            let processor_class = module.getattr("APIDefinitionProcessor").unwrap();
            let processor = processor_class.call1((None::<Py<PyAny>>,)).unwrap();
            assert!(processor.is_instance_of::<APIDefinitionProcessor>());
        });
    }

    #[test]
    fn test_error_type_usage() {
        setup_test_env();
        Python::with_gil(|py| {
            let module = PyModule::new(py, "swagger_processor").unwrap();
            swagger_processor(&module).unwrap();

            let error_type = module.getattr("APIDefinitionError").unwrap();
            let error = error_type.call1(("Test error",)).unwrap();
            assert!(error.is_instance_of::<APIDefinitionError>());
        });
    }

    #[test]
    fn test_concurrent_module_access() {
        setup_test_env();
        let handles: Vec<_> = (0..10)
            .map(|_| {
                std::thread::spawn(move || {
                    Python::with_gil(|py| {
                        let module = PyModule::new(py, "swagger_processor").unwrap();
                        let result = swagger_processor(&module);
                        assert!(result.is_ok());
                    })
                })
            })
            .collect();

        for handle in handles {
            handle.join().unwrap();
        }
    }

    #[test]
    fn test_module_docstring() {
        setup_test_env();
        Python::with_gil(|py| {
            let module = PyModule::new(py, "swagger_processor").unwrap();
            swagger_processor(&module).unwrap();

            let doc = module.getattr("__doc__").unwrap();
            assert!(doc.is_none() || doc.is_instance_of::<PyString>());
        });
    }

    #[test]
    fn test_processor_methods_availability() {
        setup_test_env();
        Python::with_gil(|py| {
            let module = PyModule::new(py, "swagger_processor").unwrap();
            swagger_processor(&module).unwrap();

            let processor_class = module.getattr("APIDefinitionProcessor").unwrap();
            let processor = processor_class.call1((None::<Py<PyAny>>,)).unwrap();

            // Test that process_api_definition method exists
            assert!(processor.getattr("process_api_definition").is_ok());
        });
    }
}
