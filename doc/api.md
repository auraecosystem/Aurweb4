# aurweb v6 /api

Specification for version 6 of the metadata REST-API

## Endpoints

Endpoints are classified in 3 categories:

* Search -> Search for packages
* Info -> Lookup information for package (exact keyword)
* Suggest -> Search for package names (max. 20 results)

### Search

Performs a search query according to the `by` parameter.

* <mark>GET</mark>`/api/v6/search/{arg}`
  <mark>GET</mark>`/api/v6/search/{by}/{arg}`
  <mark>GET</mark>`/api/v6/search/{by}/{mode}/{arg}`
    * `arg` <sub>(path; mandatory)</sub>
    * `by` <sub>(path; optional)</sub>
    * `mode` <sub>(path; optional)</sub>

#### Parameters

* `by`

    The field that is utilized in the search query
    If not specified, searching is performend with ***name-desc***
    * Type: `string`
    * Allowed values
        * `name`
        * `name-desc`
    * Default: `name-desc`

* `mode`

    The search-mode that is being used to query packages
    If not specified, searching is performend with ***contains***
    * Type: `string`
    * Allowed values
        * `contains`
        * `starts-with`
    * Default: `contains`

* `arg`

    The argument/search-term(s) for the search query
    Multiple terms/words can be supplied (space separated)
    to perform and *AND*-like query

    * Type: `string`

#### Response

Data is returned in JSON format.
Empty fields are ommitted in the output.

`200 - OK`

* PackageData

    ```json
    {
        "resultcount": 1,
        "results": [
            {
                "Name": "my-pkg",
                "Description": "Package description",
                "Version": "1.7.5-1",
                "PackageBase": "my-pkg",
                "URL": "https://example.com",
                "URLPath": "/cgit/aur.git/snapshot/my-pkg.tar.gz",
                "Maintainer": "someone",
                "Submitter": "someone",
                "FirstSubmitted": 1648375227,
                "LastModified": 1666386881,
                "OutOfDate": 1648375227,
                "NumVotes": 10,
                "Popularity": 6.463867,
                "License": [
                    "MIT",
                    "GPL3"
                ],
                "Depends": [
                    "some-pkg",
                    "another-pkg"
                ],
                "MakeDepends": [
                    "some-pkg",
                    "another-pkg"
                ],
                "OptDepends": [
                    "some-pkg",
                    "another-pkg"
                ],
                "CheckDepends": [
                    "some-pkg",
                    "another-pkg"
                ],
                "Provides": [
                    "some-pkg",
                    "another-pkg"
                ],
                "Conflicts": [
                    "some-pkg",
                    "another-pkg"
                ],
                "Replaces": [
                    "some-pkg",
                    "another-pkg"
                ],
                "Groups": [
                    "some-grp",
                    "another-grp"
                ],
                "Keywords": [
                    "some-keyword",
                    "another-keyword"
                ],
                "CoMaintainers": [
                    "someone",
                    "another-one"
                ]
            }
        ],
        "type": "search",
        "version": 6
    }
    ```

`400 - Bad Request`

* Error

    ```json
    {
        "error": "Incorrect by field specified",
        "resultcount": 1,
        "results": [],
        "type": "error",
        "version": 6
    }
    ```

### Info

Returns a list of detailed package data for one or more packages

#### Single lookup
* <mark>GET</mark>`/api/v6/info/{arg}`
  <mark>GET</mark>`/api/v6/info/{by}/{arg}`
    * `arg` <sub>(path; mandatory)</sub>
    * `by` <sub>(path; optional)</sub>

#### Multi lookup
* <mark>GET</mark>`/api/v6/info?arg=xyz&arg=abc`
  <mark>GET</mark>`/api/v6/info?by=provides&arg=xyz&arg=abc`
    * `arg` <sub>(query-string; mandatory; one or more)</sub>
    * `by` <sub>(query-string; optional)</sub>

* <mark>POST</mark>`/api/v6/info`
     * BODY (`application/x-www-form-urlencoded`):
        ```xml
        arg=one&arg=two&by=provides
        ```

#### Parameters

* `by`

    The field is being utilized in the lookup query
    If not specified, a lookup is performend with ***name***
    * Type: `string`
    * Allowed values
        * `name`
        * `depends`
        * `checkdepends`
        * `optdepends`
        * `makedepends`
        * `maintainer`
        * `submitter`
        * `provides`
        * `conflicts`
        * `replaces`
        * `keywords`
        * `groups`
        * `comaintainers`
    * Default: `name`

* `arg`

    One or more keywords

    * Type: `string` or `string-array` (depending on the endpoint)

#### Response

Data is returned in JSON format.
Empty fields are ommitted in the output.

`200 - OK`

* PackageData

    See `Search` type

`400 - Bad Request`

* Error

    See `Search` type

### Suggest

Returns a list of package names starting with the supplied argument.
Mostly used for auto-completion fields when typing.

#### Starts-with search

* <mark>GET</mark>`/api/v6/suggest/{arg}`
    * `arg` <sub>(path; mandatory)</sub>

* <mark>GET</mark>`/api/v6/suggest-pkgbase/{arg}`
    * `arg` <sub>(path; mandatory)</sub>


#### Response

Data is returned in JSON format.

`200 - OK`

* PackageNames

    ```json
    [
        "pkg1",
        "pkg2",
        "pkg3",
    ]
    ```

#### Parameters

* `arg`

    Search term (starts-with)

    * Type: `string`

## Examples

Below you'll find some basic examples for the different types of requests.

### Search

* packages containing `firefox` in the package name or description

    <mark>GET</mark>`/api/v6/search/firefox`
    <mark>GET</mark>`/api/v6/search/name-desc/firefox`
    <mark>GET</mark>`/api/v6/search/name-desc/contains/firefox`

* packages whose name start with `firefox`

    <mark>GET</mark>`/api/v6/search/name/starts-with/firefox`

* packages containing both `fire` and `fox` in the name

    <mark>GET</mark>`/api/v6/search/name/fire+fox`
    (note that `+` is a URL-encoded whitespace character)

### Info

* a package with the name `firefox`

    <mark>GET</mark>`/api/v6/info/firefox`

* packages providing `firefox`

    <mark>GET</mark>`/api/v6/info/provides/firefox`
    <mark>GET</mark>`/api/v6/info?by=provides&arg=firefox`

* packages co-maintained by `someuser`

    <mark>GET</mark>`/api/v6/info/comaintainers/someuser`
    <mark>GET</mark>`/api/v6/info?by=comaintainers&arg=someuser`

* packages with name `firefox` or `chromium`

    <mark>GET</mark>`/api/v6/info?by=name&arg=firefox&arg=chromium`

    <mark>POST</mark>`/api/v6/info`
    ```
    arg=firefox&arg=chromium&by=name
    ```

### Suggest

* packages starting with `fire`

    <mark>GET</mark>`/api/v6/suggest/fire`

* packages whose pkgbase starts with `fire`

    <mark>GET</mark>`/api/v6/suggest-pkgbase/fire`
