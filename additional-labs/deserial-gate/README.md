# Deserial Gate (Insecure Deserialization)

**Lab Name:** `deserial-gate`
**Vulnerability:** Insecure Deserialization
## Objective
The application uses Python's `pickle` module to serialize and deserialize user preferences in a cookie. Your goal is to exploit insecure deserialization to gain Remote Code Execution (RCE).

## Vulnerabilities
1. **Insecure Deserialization**: The application uses `pickle.loads` on untrusted user input from the `user_prefs` cookie.

## How to Run
This lab is part of the WebSploit Labs framework and it is running on the `deserial-gate` container on the `10.6.6.42` IP address.
Access the lab at `http://10.6.6.42:5022`.

## References
For more information on insecure deserialization vulnerabilities and secure coding practices, check out these resources:

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

