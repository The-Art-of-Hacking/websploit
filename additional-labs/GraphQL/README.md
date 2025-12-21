# GraphQL Galaxy: API Hacking Lab

**Lab Name:** `graphql-galaxy`
**Vulnerability:** GraphQL Introspection, Information Disclosure, IDOR

## Description
This lab simulates a futuristic communications hub that exposes a GraphQL API. The API is misconfigured to allow full schema introspection, revealing sensitive fields and internal types. Additionally, the resolvers lack proper authorization checks, allowing users to access data they shouldn't (IDOR).

## Learning Objectives
- Understand GraphQL Introspection and how to use it for reconnaissance.
- Identify sensitive fields in a GraphQL schema.
- Exploit IDOR vulnerabilities in GraphQL resolvers.
- Learn how to use GraphiQL to interact with the API.

## Installation
This lab is part of the WebSploit Labs framework.
To run it individually:
```bash
docker build -t graphql-galaxy .
docker run -p 5023:5023 graphql-galaxy
```

## Challenge
1.  **Reconnaissance:** Use the GraphiQL interface to inspect the available queries and types.
2.  **Introspection:** Find the hidden `api_token` field in the `User` type.
3.  **Exploitation:** Query the `user` field with the ID of the administrator (`1`) and request the `api_token`.
4.  **Flag:** The flag is the value of the administrator's `api_token`.

