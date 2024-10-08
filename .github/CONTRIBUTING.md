# Contributing to Swirl
Have an idea for a new feature or enhancement to Swirl? Find a bug in the code that you can fix?  Catch a typo in our Product Documentation? That's great!  Read on for a guide to contributing to the project.

## Code Contributions

### Branching
 To ensure a proper code review, all contributions to the project must go through a GitHub pull request. We follow a rough approximation of the [Gitflow branching model](https://nvie.com/posts/a-successful-git-branching-model/) for the core project code. 
 
 All code contributions should go on the `develop` branch, which helps ensure that our `main` branch remains stable. When submitting core code PRs to Swirl, please create a branch off of `develop` and fill out the PR Template completely.

For more general information about contributing to projects on Github, check out the [GitHub documentation](https://docs.github.com/en/get-started/quickstart/contributing-to-projects) on this very subject.

### Testing
When submitting a PR, we ask that you please describe in detail how you tested your changes, including details of your testing environment and the tests you ran to validate your change.  Screenshots or short videos showing the change or new feature working correctly are also very helpful.

## New SearchProviders
If you are contributing a new SearchProvider to the project, please target your new JSON file to the `SearchProviders/untested` directory of the `develop` branch.

New SearchProvider JSON should contain, at minimum:
- Complete and correct `url` and `query_template` fields.
- Any custom headers required by the source specified in the `http_request_headers` field.
- Any available `response_mappings` values returned by the source, especially `FOUND=` and `RESULTS=` values.
- Valid `result_mappings` for Swirl's supported fields (`title`, `body`, `author`, `date_published`, and `url`) plus any relevant PAYLOAD selections based on the full response.
- At least one Tag value appropriate to the source (`tags` field).
- Accurate placeholder for the authentication required by the source, when applicable.

Consult the [User Guide](https://docs.swirl.today/User-Guide.html) for more details on SearchProvider JSON.

Screenshots of working SearchProviders are very helpful as well, especially if the source you're connecting to is private (not-publicly searchable) or requires authentication.

## Product Documentation
Swirl's [Product Documentation](https://docs.swirl.today/) is maintained _only on the `main` branch_ of the repo, in the `docs/` directory.  It is published to our documentation website via a GitHub Pages workflow.  When submitting PRs for documentation corrections, updates, or additions, please create a branch off of `main` and fill out the PR Template completely.

If you submit a code change that warrants an update to the Product Documentation, or if you are adding a new feature to Swirl, we expect _a separate PR_ off `main` that contains the related documentation updates or additions.

## Support
Have questions about Swirl?  Need some additional guidance on your journey toward contributing to the project?  We're here to help!

* Check out the [Product Documentation](https://docs.swirl.today/)

* Join the [Swirl Community on Slack](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-2sfwvhwwg-mMn9tcKhAbqXbrV~9~Y1eA)!

* Email: [support@swirl.today](mailto:support@swirl.today) with issues, requests, questions, etc. - we'd love to hear from you!

Many thanks!

~ Team Swirl