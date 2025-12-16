# Path Traversal Lab

This lab demonstrates a Path Traversal (also known as Directory Traversal) vulnerability.

## Scenario
The application is a "Document Viewer" that allows users to view public files stored in a specific directory. It takes a filename as a parameter and displays its content.

## Goal
Exploit the path traversal vulnerability to access files outside the intended directory, such as system configuration files.

## Instructions

1. **Access the Lab**:
   - URL: `http://localhost:5003`

2. **Analyze functionality**:
   - Click on the links for `hello.txt` or `notes.txt`.
   - Observe the URL parameter: `?file=hello.txt`.

3. **Identify Vulnerability**:
   - The application likely joins a base directory with your input: `open(os.path.join('files', filename))`
   - Try using `../` sequences to move up the directory tree.

4. **Challenge**:
   - Access the `/etc/passwd` file.
   - Payload: `../../../../etc/passwd` (Adjust the depth as needed).
   - Try to read the application source code (`../path-traversal-example-app.py` or similar).

## Explanation
The application fails to validate that the resolved path is still within the intended directory. By providing `../`, an attacker can traverse out of the `files/` folder and access any file the application process has read permissions for.

