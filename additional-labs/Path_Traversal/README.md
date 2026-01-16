# Path Traversal Lab

**Lab Name:** `maze-walker`
**Vulnerability:** Path Traversal
This lab demonstrates a Path Traversal (also known as Directory Traversal) vulnerability.

## Scenario
The application is a "Document Viewer" that allows users to view public files stored in a specific directory. It takes a filename as a parameter and displays its content.

## Goal
Exploit the path traversal vulnerability to access files outside the intended directory, such as system configuration files.

## Instructions

1. **Access the Lab**:
   - This is running on the `maze-walker` container on the `10.6.6.35` IP address. Access the lab at `http://10.6.6.35:5003`

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

## References
For more information on path traversal vulnerabilities and secure coding practices, check out these resources:

## Live Training
**Upcoming Live Cybersecurity and AI Training in O'Reilly:** [Register before it is too late](https://learning.oreilly.com/search/?q=omar%20santos&type=live-course&rows=100&language_with_transcripts=en) (free with O'Reilly Subscription)

## Reading List

- **Redefining Hacking**
A Comprehensive Guide to Red Teaming and Bug Bounty Hunting in an AI-driven World [Available on O'Reilly](https://learning.oreilly.com/library/view/redefining-hacking-a/9780138363635/)

- **Developing Cybersecurity Programs and Policies in an AI-Driven World**  
  Explore strategies for creating robust cybersecurity frameworks in an AI-centric environment. [Available on O'Reilly](https://learning.oreilly.com/library/view/developing-cybersecurity-programs/9780138073992)

- **Beyond the Algorithm: AI, Security, Privacy, and Ethics**  
  Gain insights into the ethical and security challenges posed by AI technologies. [Available on O'Reilly](https://learning.oreilly.com/library/view/beyond-the-algorithm/9780138268442)

- **The AI Revolution in Networking, Cybersecurity, and Emerging Technologies** Understand how AI is transforming networking and cybersecurity landscapes.  
[Available on O'Reilly](https://learning.oreilly.com/library/view/the-ai-revolution/9780138293703)

## Video Courses  

- **Building the Ultimate Cybersecurity Lab and Cyber Range (video)** [Available on O'Reilly](https://learning.oreilly.com/course/building-the-ultimate/9780138319090/)

- **Defending and Deploying AI (video)**  This course provides a comprehensive, hands-on journey into modern AI applications for technology and security professionals, covering AI-enabled programming, networking, and cybersecurity to help learners master AI tools for dynamic information retrieval, automation, and operational efficiency. [Available on O'Reilly](https://www.oreilly.com/videos/defending-and-deploying/9780135463727/)

- **AI-Enabled Programming, Networking, and Cybersecurity**
Learn to use AI for cybersecurity, networking, and programming tasks. [Available on O'Reilly](https://learning.oreilly.com/course/ai-enabled-programming-networking/9780135402696/)

- **Securing Generative AI**
Explore security for deploying and developing AI applications, RAG, agents, and other AI implementations. [Available on O'Reilly](https://learning.oreilly.com/course/securing-generative-ai/9780135401804/)

- **Certified Ethical Hacker (CEH), Latest Edition** [Available on O'Reilly](https://learning.oreilly.com/course/certified-ethical-hacker/9780135395646/)

## Additional Resources

- **Hacking Scenarios (Labs) in O'Reilly**: [https://hackingscenarios.com](https://hackingscenarios.com)
- **GitHub Repository**: [Visit GitHub Repo](https://hackerrepo.org)
- **WebSploit Labs**: [Visit WebSploit Labs](https://websploit.org)
- **NetAcad Ethical Hacker Free Course** - [Available (free) on NetAcad Skills for All](https://www.netacad.com/courses/ethical-hacker?courseLang=en-US)
- **The Art of Hacking** - [Visit The Art of Hacking](https://theartofhacking.org)
- **Hacking Scenarios (Labs) in O'Reilly** - [https://hackingscenarios.com](https://hackingscenarios.com)
- **GitHub Repository** - [Visit GitHub Repo](https://hackerrepo.org)
- **WebSploit Labs** - [Visit WebSploit Labs](https://websploit.org)
- **NetAcad Ethical Hacker Free Course** - [Available (free) on NetAcad Skills for All](https://www.netacad.com/courses/ethical-hacker?courseLang=en-US)