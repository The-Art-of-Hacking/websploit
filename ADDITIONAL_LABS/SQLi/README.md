# SQL Injection (SQLi) Lab

This lab demonstrates a classic SQL Injection vulnerability in a login form.

## Scenario
The application is a secure "Login Portal" requiring a username and password. The backend constructs a database query by concatenating user input directly into the SQL string.

## Goal
Bypass the authentication mechanism to log in as the administrator without knowing the password.

## Instructions

1. **Access the Lab**:
   - URL: `http://localhost:5001`

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

