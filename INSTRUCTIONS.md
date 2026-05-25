Challenge Details:
As a CircleCI Field Engineer we’re expected to not only hold strong knowledge in our core product and CI/CD principles but show proficiency in the various technologies common to a CI/CD pipeline.
 
To demonstrate this proficiency, we ask candidates to create a pipeline that touches on several competencies.
 
Create a CircleCI configuration that builds a tested docker image and publishes an artifact. The pipeline must meet the following criteria:
* exists in a public VCS repo connected to CircleCI
* uses a custom docker image generated during the pipeline
* performs testing with results that can be collected by CircleCI
* includes use of a database such as postgres, mysql, or mongodb
* make use of a “sidecar” or secondary container for this
* DB container may be off-the-shelf image
* performs conditional work during the execution of the pipeline to limit unnecessary work (may be based on PR status, files changes, success or failures of upstream work)
* includes shell scripting and non-scripting language (either as the application under test, or in config file)
* publishes an artifact to PaaS, FaaS, or IaaS of your choice
* only on merge to default branch
* credentials may no be accessible outside of approved builds
* ideally makes use of OIDC

Once you are satisfied, and have a working (green) build, please submit a brief writeup and submit it to the link below. The writeup should be written as if directed towards a customer looking for a reference pipeline.
* Include link to the VCS Repo, and a passing CCI build link.
* Explain the overall architecture
* what it does
* how components are mapped together
* Explain the unique value and optimizations made leveraging CircleCI features
* Outline potential future optimizations or trade-offs to consider
 
Resources:
You may be interested in using the following tools/projects:
* Testing Frameworks
* dgoss or serverspec for container testing
* Junit
* Pytest
* Gotest
* Python Developer?
* Django
* Flask w/ SQL Alchemy
* Peewee ORM
* Java Developer?
* Spring Boot
* Golang Developer?
* https://gorm.io/docs/

You may want to start with the following CCI docs:
CCI Configuration Reference - https://circleci.com/docs/guides/orchestrate/pipelines/
