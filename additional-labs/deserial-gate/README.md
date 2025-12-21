# Deserial Gate (Insecure Deserialization)

## Objective
The application uses Python's `pickle` module to serialize and deserialize user preferences in a cookie. Your goal is to exploit insecure deserialization to gain Remote Code Execution (RCE).

## Vulnerabilities
1. **Insecure Deserialization**: The application uses `pickle.loads` on untrusted user input from the `user_prefs` cookie.

## How to Run
Access the lab at `http://<IP>:5022` or `http://localhost:5022`.

