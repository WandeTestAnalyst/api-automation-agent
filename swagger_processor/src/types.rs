use pyo3::exceptions::PyException;
use serde_json::Value;

// Custom exception for API definition errors
pyo3::create_exception!(api_definition, APIDefinitionError, PyException);

// Internal Rust structures
#[derive(Debug, Clone, PartialEq)]
pub struct APIPath {
    pub path: String,
    pub yaml: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct APIVerb {
    pub verb: String,
    pub path: String,
    pub root_path: String,
    pub yaml: String,
}

#[derive(Debug, Clone, PartialEq)]
pub enum APIDef {
    Path(APIPath),
    Verb(APIVerb),
}

// Optimized data structure for processing paths
#[derive(Debug)]
pub struct PathGroup {
    pub normalized_path: String,
    pub path_entries: Vec<(String, Value)>, // Avoid reference lifetimes
}

impl PathGroup {
    pub fn new(normalized_path: String) -> Self {
        Self {
            normalized_path,
            path_entries: Vec::new(),
        }
    }

    pub fn add_path(&mut self, original_path: String, path_data: Value) {
        self.path_entries.push((original_path, path_data));
    }

    pub fn len(&self) -> usize {
        self.path_entries.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_api_path_creation() {
        let path = APIPath {
            path: "/users".to_string(),
            yaml: "openapi: 3.0.0".to_string(),
        };
        assert_eq!(path.path, "/users");
        assert_eq!(path.yaml, "openapi: 3.0.0");
    }

    #[test]
    fn test_api_verb_creation() {
        let verb = APIVerb {
            verb: "GET".to_string(),
            path: "/users".to_string(),
            root_path: "/users".to_string(),
            yaml: "openapi: 3.0.0".to_string(),
        };
        assert_eq!(verb.verb, "GET");
        assert_eq!(verb.path, "/users");
        assert_eq!(verb.root_path, "/users");
    }

    #[test]
    fn test_api_def_enum_path() {
        let path = APIPath {
            path: "/users".to_string(),
            yaml: "test".to_string(),
        };
        let api_def = APIDef::Path(path.clone());
        
        match api_def {
            APIDef::Path(p) => assert_eq!(p, path),
            _ => panic!("Expected Path variant"),
        }
    }

    #[test]
    fn test_api_def_enum_verb() {
        let verb = APIVerb {
            verb: "POST".to_string(),
            path: "/users".to_string(),
            root_path: "/users".to_string(),
            yaml: "test".to_string(),
        };
        let api_def = APIDef::Verb(verb.clone());
        
        match api_def {
            APIDef::Verb(v) => assert_eq!(v, verb),
            _ => panic!("Expected Verb variant"),
        }
    }

    #[test]
    fn test_path_group_new() {
        let group = PathGroup::new("/users".to_string());
        assert_eq!(group.normalized_path, "/users");
        assert_eq!(group.len(), 0);
        assert!(group.path_entries.is_empty());
    }

    #[test]
    fn test_path_group_add_path() {
        let mut group = PathGroup::new("/users".to_string());
        let path_data = json!({"get": {"summary": "Get users"}});
        
        group.add_path("/api/v1/users".to_string(), path_data.clone());
        
        assert_eq!(group.len(), 1);
        assert_eq!(group.path_entries[0].0, "/api/v1/users");
        assert_eq!(group.path_entries[0].1, path_data);
    }

    #[test]
    fn test_path_group_multiple_paths() {
        let mut group = PathGroup::new("/users".to_string());
        
        group.add_path("/api/v1/users".to_string(), json!({"get": {}}));
        group.add_path("/api/v2/users".to_string(), json!({"post": {}}));
        
        assert_eq!(group.len(), 2);
        assert_eq!(group.path_entries[0].0, "/api/v1/users");
        assert_eq!(group.path_entries[1].0, "/api/v2/users");
    }

    #[test]
    fn test_path_group_empty_len() {
        let group = PathGroup::new("/test".to_string());
        assert_eq!(group.len(), 0);
    }

    #[test]
    fn test_api_path_clone() {
        let original = APIPath {
            path: "/test".to_string(),
            yaml: "yaml content".to_string(),
        };
        let cloned = original.clone();
        
        assert_eq!(original, cloned);
        assert_eq!(original.path, cloned.path);
        assert_eq!(original.yaml, cloned.yaml);
    }

    #[test]
    fn test_api_verb_clone() {
        let original = APIVerb {
            verb: "DELETE".to_string(),
            path: "/test".to_string(),
            root_path: "/test".to_string(),
            yaml: "yaml content".to_string(),
        };
        let cloned = original.clone();
        
        assert_eq!(original, cloned);
        assert_eq!(original.verb, cloned.verb);
    }

    #[test]
    fn test_api_def_clone() {
        let path = APIPath {
            path: "/test".to_string(),
            yaml: "yaml".to_string(),
        };
        let original = APIDef::Path(path);
        let cloned = original.clone();
        
        assert_eq!(original, cloned);
    }
}