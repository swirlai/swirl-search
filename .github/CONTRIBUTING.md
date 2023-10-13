# Contributing to Swirl
Have an idea for a new feature or enhancement to Swirl? Find a bug in the code that you can fix?  Catch a typo in our Product Documentation? That's great!  Read on for guidance on contributing to the project.

## Code Contributions

### Branching
 To ensure a proper code review, all contributions to the project must go through a GitHub pull request. We follow a rough approximation of the [Gitflow branching model](https://nvie.com/posts/a-successful-git-branching-model/) for the core project code. 
 
 All code contributions should go on the `develop` branch, which helps ensure that our `main` branch remains stable. When submitting core code PRs to Swirl, please create a branch off of `develop` and fill out the PR Template completely.

For more general information about contributing to projects on Github, check out the [GitHub documentation](https://docs.github.com/en/get-started/quickstart/contributing-to-projects) on this very subject.

### Testing
When submitting a PR, we ask that you please describe in detail how you tested your changes, including details of your testing environment and the tests you ran to validate your change.  Screenshots or short videos showing the change or new feature working correctly are also very helpful.

## SearchProvider Contributions
If you are contributing a new SearchProvider to the project, please land your new JSON file in the `SearchProviders/untested` directory of the `develop` branch.

_(add additional content about testing new SPs here)_

Screenshots of working SearchProviders are very helpful, especially if the source you're connecting to is private (not-publicly searchable) or requires authentication.

## Documentation Contributions
Swirl's [Product Documentation](https://docs.swirl.today/) is maintained _only on the `main` branch_ of the repo, in the `docs/` directory.  It is published to our documenation website via a GitHub Pages workflow.  When submitting PRs for documentation corrections, updates, or additions, please create a branch off of `main` and fill out the PR Template completely.

If you submit a code change that warrants an update to the Product Documentation, or if you are adding a new feature to Swirl, we expect _a separate PR_ off `main` that contains only the related documentation updates or additions.

## Support
Have questions about Swirl?  Need some additional guidance on your journey toward contributing to the project?  We're here to help!

* Check out the [Product Documentation](https://docs.swirl.today/)

* Join the [Swirl Metasearch Community on Slack](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw)!

* Email: [support@swirl.today](mailto:support@swirl.today) with issues, requests, questions, etc. - we'd love to hear from you!

Many thanks!

~ Team Swirl