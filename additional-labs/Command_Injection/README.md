# Command Injection Lab

**Lab Name:** `shell-inject`
**Vulnerability:** OS Command Injection

This lab demonstrates an OS Command Injection vulnerability in a web application.

## Scenario
The application is a "Network Diagnostics" tool that allows users to ping an IP address. The application takes the user input and passes it directly to a system shell command without proper sanitization.

## Goal
Exploit the command injection vulnerability to execute arbitrary commands on the underlying server.

## Instructions

1. **Access the Lab**: 
   - This is running on the `shell-inject` container on the `10.6.6.34` IP address. Access the lab at `http://10.6.6.34:5002`

## Explanation
The application constructs a shell command like this:
```python
command = f"ping -c 3 {target}"
subprocess.run(command, shell=True, ...)
```
Because `shell=True` is used and `target` is not sanitized, an attacker can terminate the `ping` command and start a new one.

## References
For more information on command injection vulnerabilities and secure coding practices, check out these resources:

## Live Training
**Upcoming Live Cybersecurity and AI Training in O'Reilly:** [Register before it is too late](https://learning.oreilly.com/search/?q=omar%20santos&type=live-course&rows=100&language_with_transcripts=en) (free with O'Reilly Subscription)

## Reading List

- **Redefining Hacking**
A Comprehensive Guide to Red Teaming and Bug Bounty Hunting in an AI-driven World [Available on O'Reilly](https://learning.oreilly.com/library/view/redefining-hacking-a/9780138363635/)

- **Developing Cybersecurity Programs and Policies in an AI-Driven World**  
  Explore strategies for creating robust cybersecurity frameworks in an AI-centric environment. [Available on O'Reilly](https://learning.oreilly.com/library/view/developing-cybersecurity-programs/9780138073992)

- **Beyond the Algorithm: AI, Security, Privacy, and Ethics**  
  Gain insights into the ethical and security challenges posed by AI technologies. [Available on O'Reilly](https://learning.oreilly.com/library/view/beyond-the-algorithm/9780138268442)

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


