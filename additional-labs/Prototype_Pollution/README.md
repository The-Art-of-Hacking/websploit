# Prototype Pollution & DOM Clobbering Lab

**Lab Name:** `proto-pollute`  
**Vulnerability:** Prototype Pollution, DOM Clobbering

This lab is part of the WebSploit Labs framework and it is running on the `proto-pollute` container on the `10.6.6.45` IP address.
Access the lab at `http://10.6.6.45:5004`.

## Learning Objectives
By completing this lab, students will learn to:
- Understand JavaScript prototype chain and how it can be exploited
- Exploit server-side prototype pollution to bypass authentication
- Perform DOM clobbering attacks to hijack application logic
- Assess the security impact of unsafe object merging
- Implement proper defenses against these vulnerability classes

## Prerequisites

- Basic understanding of JavaScript objects and prototypes
- Familiarity with HTTP requests and JSON
- Basic knowledge of web application security
- Browser developer tools experience

## Walkthrough

1. Access the lab at `http://10.6.6.45:5004`.
2. Click on "Lab 1: DOM Clobbering".
3. Click on "Inject & Reload".
4. Observe that the script URL has been hijacked.
5. Click on "Lab 2: Server-Side Prototype Pollution".
6. In the JSON input field, enter the pollution payload:
```json
{"__proto__": {"isAdmin": true}}
```
7. Click on "Send Update".
8. Observe that the response indicates pollution was successful.
9. Click on "Check Admin Access".
10. You should now have admin access and receive the flag!

## Explanation
The application is vulnerable to Prototype Pollution because it uses an unsafe recursive merge function. This allows an attacker to pollute the `Object.prototype` and gain unauthorized admin access.

## Mitigation
The application should use a safe merge function that validates keys and does not allow the attacker to pollute the `Object.prototype`.

## References
For more information on prototype pollution and DOM clobbering vulnerabilities and secure coding practices, check out these resources:
- [WebSploit Labs Prototype Pollution Vulnerability](../../knowledge-base/vulnerabilities/prototype-pollution.md)
- [WebSploit Labs DOM Clobbering Vulnerability](../../knowledge-base/vulnerabilities/dom-clobbering.md)
- [WebSploit Labs Prototype Pollution Mitigation](../../knowledge-base/mitigations/prototype-pollution-mitigation.md)
- [WebSploit Labs DOM Clobbering Mitigation](../../knowledge-base/mitigations/dom-clobbering-mitigation.md)

- [OWASP Prototype Pollution](https://owasp.org/www-community/attacks/Prototype_Pollution)
- [PortSwigger - Prototype Pollution](https://portswigger.net/web-security/prototype-pollution)
- [PortSwigger - DOM Clobbering](https://portswigger.net/web-security/dom-based/dom-clobbering)

