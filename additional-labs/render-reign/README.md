# Render Reign (Server-Side Template Injection)

**Lab Name:** `render-reign`
**Vulnerability:** Server-Side Template Injection

## Objective
The application uses a template engine to render user input. Your goal is to exploit Server-Side Template Injection (SSTI) to gain Remote Code Execution (RCE).

## Vulnerabilities
1. **SSTI**: The application directly concatenates user input into the template string.

## How to Run
This lab is part of the WebSploit Labs framework and it is running on the `render-reign` container on the `10.6.6.41` IP address.
Access the lab at `http://10.6.6.41:5021`.

## Walkthrough
1. Access the lab at `http://10.6.6.41:5021`.
2. Enter your name to generate a custom badge.
3. Observe the template string: `Hello, %s!`.
4. Try to inject a payload to execute arbitrary code.
5. Payload: `{{7*7}}`
6. The output should be `49`.

    
## Explanation
The application is vulnerable to Server-Side Template Injection because it directly concatenates user input into the template string. This allows an attacker to inject arbitrary code into the template.

## Mitigation
The application should use a template engine that is secure against Server-Side Template Injection. The application should also use a template engine that is secure against Server-Side Template Injection.

## References
For more information on Server-Side Template Injection vulnerabilities and secure coding practices, check out these resources:

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