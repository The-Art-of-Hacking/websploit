# SQL Injection (SQLi) Lab

**Lab Name:** `sqli-breach`
**Vulnerability:** SQL Injection

This lab is part of the WebSploit Labs framework and it is running on the `sqli-breach` container on the `10.6.6.33` IP address.
Access the lab at `http://10.6.6.33:5001`.

## Scenario
The application is a secure "Login Portal" requiring a username and password. The backend constructs a database query by concatenating user input directly into the SQL string.

## Goal
Bypass the authentication mechanism to log in as the administrator without knowing the password.

## Instructions

1. **Access the Lab**:
   - This is running on the `sqli-breach` container on the `10.6.6.33` IP address. Access the lab at `http://10.6.6.33:5001`

2. **Analyze functionality**:
   - Try logging in with random credentials.
   - Observe the error message.

3. **Identify Vulnerability**:
   - The application likely uses a query like:
     `SELECT * FROM users WHERE username = '$username' AND password = '$password'`
   - Try injecting SQL syntax (single quotes `'`) to break the query structure.

4. **Challenge**:
   - Log in as `admin`.
   - Payload Example (Username): `admin' --` or `admin' #` (Comment out the rest of the query).
   - Payload Example (Bypass Password): `admin' OR '1'='1`
   - Retrieve the administrator's secret flag.

## Explanation
The vulnerability exists because user input is not sanitized or parameterized.
```python
query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
```
Inputting `admin' --` changes the query to:
`SELECT * FROM users WHERE username = 'admin' --' AND password = '...'`
The `--` comments out the password check, allowing login based solely on the username.

## Mitigation
The application should use a parameterized query instead of a concatenated query.
```python
query = "SELECT * FROM users WHERE username = %s AND password = %s"
cursor.execute(query, (username, password))
```

## References
For more information on SQL Injection vulnerabilities and secure coding practices, check out these resources:
- [OWASP SQL Injection](https://owasp.org/www-community/attacks/SQL_Injection)
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
