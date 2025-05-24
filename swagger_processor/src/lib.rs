use pyo3::prelude::*;
mod types;
mod logger;
mod processor;
mod utils;

use processor::APIDefinitionProcessor;
use types::APIDefinitionError;

/// PyO3 module definition
#[pymodule]
fn swagger_processor(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<APIDefinitionProcessor>()?;
    m.add("APIDefinitionError", m.py().get_type::<APIDefinitionError>())?;
    Ok(())
}