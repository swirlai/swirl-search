![SWIRL Logo](./images/swirl_logo_notext_200.jpg)

<br/>

# HELP WANTED - SWIRL TO DO'S

* Resolve the [known issues in the last release](RELEASE_NOTES_1.3.md#known-issues)

* Create new [SearchProviders](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#searchproviders) or [Connectors](https://github.com/sidprobstein/swirl-search/wiki/4.-Object-Reference#develop-your-own)

* Fix Celery; currently SWIRL uses the sqlite database to manage state, because of NACK/timeout issues with rabbitmq. 

All celery tasks are configured with ignore_result=True to prevent the timeout from causing RabbitMQ to explode.

[swirl/tasks.py](../swirl/tasks.py)

```
@shared_task(name='federate', ignore_result=True)
```

Please [contact support](#support) for access to the old repo, to work on this, or send a PR :-) if you fixed it.

<br/>

# Support

:small_blue_diamond: [Create an Issue](https://github.com/sidprobstein/swirl-search/issues) if something doesn't work, isn't clear, or should be documented - we'd love to hear from you!

:small_blue_diamond: Paid support and consulting are available... [contact SWIRL](mailto:support@swirl.today) for more information.
