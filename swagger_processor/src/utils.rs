// Optimized helper functions with better string handling
pub fn normalize_path(path: &str) -> String {
    let path = path.trim_start_matches('/');
    let parts: Vec<&str> = path.split('/').filter(|p| !p.is_empty()).collect();

    if parts.is_empty() {
        return "/".to_string();
    }

    let mut start_index = 0;

    // Skip "api" if present
    if start_index < parts.len() && parts[start_index] == "api" {
        start_index += 1;
    }

    // Skip version prefix (e.g., "v1", "v2") if present
    if start_index < parts.len() {
        let part = parts[start_index];
        if part.len() > 1 && part.starts_with('v') {
            let version_part = &part[1..];
            if version_part.chars().all(|c| c.is_ascii_digit()) {
                start_index += 1;
            }
        }
    }

    if start_index < parts.len() {
        let mut result = String::with_capacity(path.len() + 1);
        result.push('/');
        result.push_str(&parts[start_index..].join("/"));
        result
    } else {
        "/".to_string()
    }
}

pub fn get_root_path(path: &str) -> String {
    let path = path.trim_start_matches('/');
    if let Some(slash_pos) = path.find('/') {
        let first_part = &path[..slash_pos];
        if !first_part.is_empty() {
            let mut result = String::with_capacity(first_part.len() + 1);
            result.push('/');
            result.push_str(first_part);
            result
        } else {
            "/".to_string()
        }
    } else if !path.is_empty() {
        let mut result = String::with_capacity(path.len() + 1);
        result.push('/');
        result.push_str(path);
        result
    } else {
        "/".to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    mod normalize_path_tests {
        use super::*;

        #[test]
        fn test_empty_path() {
            assert_eq!(normalize_path(""), "/");
        }

        #[test]
        fn test_root_path() {
            assert_eq!(normalize_path("/"), "/");
        }

        #[test]
        fn test_simple_path() {
            assert_eq!(normalize_path("/users"), "/users");
        }

        #[test]
        fn test_path_with_api_prefix() {
            assert_eq!(normalize_path("/api/users"), "/users");
        }

        #[test]
        fn test_path_with_version() {
            assert_eq!(normalize_path("/v1/users"), "/users");
            assert_eq!(normalize_path("/v2/users"), "/users");
            assert_eq!(normalize_path("/v10/users"), "/users");
        }

        #[test]
        fn test_path_with_api_and_version() {
            assert_eq!(normalize_path("/api/v1/users"), "/users");
            assert_eq!(normalize_path("/api/v2/users"), "/users");
            assert_eq!(normalize_path("/api/v10/users"), "/users");
        }

        #[test]
        fn test_complex_path() {
            assert_eq!(
                normalize_path("/api/v1/users/123/posts"),
                "/users/123/posts"
            );
        }

        #[test]
        fn test_path_without_leading_slash() {
            assert_eq!(normalize_path("users"), "/users");
            assert_eq!(normalize_path("api/v1/users"), "/users");
        }

        #[test]
        fn test_version_not_numeric() {
            assert_eq!(normalize_path("/v1a/users"), "/v1a/users");
            assert_eq!(normalize_path("/version/users"), "/version/users");
            assert_eq!(normalize_path("/v/users"), "/v/users");
        }

        #[test]
        fn test_api_only() {
            assert_eq!(normalize_path("/api"), "/");
            assert_eq!(normalize_path("api"), "/");
        }

        #[test]
        fn test_version_only() {
            assert_eq!(normalize_path("/v1"), "/");
            assert_eq!(normalize_path("v2"), "/");
        }

        #[test]
        fn test_api_and_version_only() {
            assert_eq!(normalize_path("/api/v1"), "/");
            assert_eq!(normalize_path("api/v2"), "/");
        }

        #[test]
        fn test_multiple_slashes() {
            assert_eq!(normalize_path("//api//v1//users"), "/users");
            assert_eq!(normalize_path("///users///posts///"), "/users/posts");
        }

        #[test]
        fn test_trailing_slash() {
            assert_eq!(normalize_path("/users/"), "/users");
            assert_eq!(normalize_path("/api/v1/users/"), "/users");
        }

        #[test]
        fn test_single_letter_after_api() {
            assert_eq!(normalize_path("/api/a"), "/a");
            assert_eq!(normalize_path("/api/x/users"), "/x/users");
        }

        #[test]
        fn test_version_with_zero() {
            assert_eq!(normalize_path("/v0/users"), "/users");
            assert_eq!(normalize_path("/v01/users"), "/users");
        }

        #[test]
        fn test_case_sensitivity() {
            assert_eq!(normalize_path("/API/V1/users"), "/API/V1/users");
            assert_eq!(normalize_path("/Api/v1/users"), "/Api/users");
        }

        #[test]
        fn test_deep_nesting() {
            assert_eq!(
                normalize_path("/api/v1/users/123/posts/456/comments"),
                "/users/123/posts/456/comments"
            );
        }
    }

    mod get_root_path_tests {
        use super::*;

        #[test]
        fn test_empty_path() {
            assert_eq!(get_root_path(""), "/");
        }

        #[test]
        fn test_root_path() {
            assert_eq!(get_root_path("/"), "/");
        }

        #[test]
        fn test_single_segment() {
            assert_eq!(get_root_path("/users"), "/users");
            assert_eq!(get_root_path("users"), "/users");
        }

        #[test]
        fn test_multiple_segments() {
            assert_eq!(get_root_path("/users/123"), "/users");
            assert_eq!(get_root_path("users/123/posts"), "/users");
        }

        #[test]
        fn test_deep_path() {
            assert_eq!(get_root_path("/users/123/posts/456/comments"), "/users");
        }

        #[test]
        fn test_path_without_leading_slash() {
            assert_eq!(get_root_path("users/123"), "/users");
            assert_eq!(get_root_path("api/v1/users"), "/api");
        }

        #[test]
        fn test_trailing_slash() {
            assert_eq!(get_root_path("/users/"), "/users");
            assert_eq!(get_root_path("/users/123/"), "/users");
        }

        #[test]
        fn test_multiple_leading_slashes() {
            assert_eq!(get_root_path("//users/123"), "/users");
        }

        #[test]
        fn test_empty_segments() {
            assert_eq!(get_root_path("/users//123"), "/users");
            assert_eq!(get_root_path("//users///123//"), "/users");
        }

        #[test]
        fn test_single_character_segments() {
            assert_eq!(get_root_path("/a/b/c"), "/a");
            assert_eq!(get_root_path("x/y/z"), "/x");
        }

        #[test]
        fn test_numeric_root() {
            assert_eq!(get_root_path("/123/users"), "/123");
            assert_eq!(get_root_path("456/posts"), "/456");
        }

        #[test]
        fn test_special_characters() {
            assert_eq!(get_root_path("/api-v1/users"), "/api-v1");
            assert_eq!(get_root_path("/users_db/records"), "/users_db");
        }
    }

    mod integration_tests {
        use super::*;

        #[test]
        fn test_normalize_then_get_root() {
            let normalized = normalize_path("/api/v1/users/123/posts");
            assert_eq!(normalized, "/users/123/posts");

            let root = get_root_path(&normalized);
            assert_eq!(root, "/users");
        }

        #[test]
        fn test_various_api_paths() {
            let test_cases = vec![
                ("/api/v1/users", "/users", "/users"),
                ("/api/v2/posts/123", "/posts/123", "/posts"),
                ("/v1/comments", "/comments", "/comments"),
                ("/api/orders", "/orders", "/orders"),
                ("/users/123/profile", "/users/123/profile", "/users"),
            ];

            for (input, expected_normalized, expected_root) in test_cases {
                let normalized = normalize_path(input);
                assert_eq!(
                    normalized, expected_normalized,
                    "Failed normalize for: {}",
                    input
                );

                let root = get_root_path(&normalized);
                assert_eq!(root, expected_root, "Failed get_root for: {}", input);
            }
        }

        #[test]
        fn test_edge_cases_combination() {
            // Test that both functions handle edge cases consistently
            let edge_cases = vec!["", "/", "///", "/api", "/v1", "/api/v1"];

            for case in edge_cases {
                let normalized = normalize_path(case);
                let root = get_root_path(&normalized);

                // Both should return "/" for these edge cases
                assert_eq!(normalized, "/", "Normalize failed for: {}", case);
                assert_eq!(root, "/", "Get root failed for: {}", case);
            }
        }

        #[test]
        fn test_performance_long_paths() {
            let long_path = format!("/api/v1/{}", "segment/".repeat(100));
            let normalized = normalize_path(&long_path);
            let root = get_root_path(&normalized);

            assert!(normalized.starts_with("/segment"));
            assert_eq!(root, "/segment");
        }

        #[test]
        fn test_unicode_paths() {
            assert_eq!(normalize_path("/api/v1/用户"), "/用户");
            assert_eq!(get_root_path("/用户/123"), "/用户");
        }
    }
}
