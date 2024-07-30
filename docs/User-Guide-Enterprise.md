---
layout: default
title: User Guide
nav_order: 8
---
<details markdown="block">
  <summary>
    Table of Contents
  </summary>
  {: .text-delta }
- TOC
{:toc}
</details>

# User Guide - Enterprise Edition

{: .warning }
This version applies to the Enterprise Edition of SWIRL!

# Glossary

The following new terms are used when referring to SWIRL Enterprise products.

| Word | Explanation | 
| ---------- | ---------- |
| AIProvider | A configuration of a Generative AI or LLM. It includes metadata identifying the type of model used, API key, and more. (Enterprise Edition only) |
| Chat | A SWIRL object that stores message objects, for AI Co-Pilot | 
| Message | A SWIRL object that contains some message either to or from a GAI/LLM | 
| Prompt | A SWIRL object that configures a GAI or LLM for use in various AI roles such as RAG or chat. (Enterprise Edition only) |

TBD: link to the Overview about Co-Pilot

# Accessing your AI Co-Pilot

* Open this URL with a browser: <http://localhost:8000/galaxy/chat/> 

*If the SWIRL login page appears*:

![SWIRL Login](images/swirl_login-galaxy_dark.png)

Enter username `admin` and password `password`, then click `Login`.

{: .warning }
If you receive a warning about the password being compromised or in a recent data breach, you [Change the super user password](Admin-Guide.md#changing-a-super-user-password).

*If your organizations SSO page appears*:

![TBD SSO page](TBD)

Login as usual. 

Regardless of the method you use, you should be redirected to the AI Co-Pilot:

![](TBD)

If you encounter an error message, [contact support](TBD).

# Starting a Conversation

* Use the input box to send a message to the Co-Pilot.

A good first thing to try is `What sources do I have access to?`

![](TBD)

The Co-Pilot should reply within 5 seconds:

![](TBD)

If it doesn't, consult the [Troubleshooting Guide](TBD)

* Converse with the Co-Pilot with the goal of finding some information. For example:

```
Tell me about the history of
```

![](TBD)







