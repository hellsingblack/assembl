API Documentation
===============================================================================

It should be noted that all paths end with a foreward slash.



Discussions
-------------------------------------------------------------------------------

A `Discussion` object takes the following form:

```json
{
  "id": 1, // integer
  "topic": "Climate Change", // string
  "slug": "climate-change", // string, slug
  "creation_date": "2013-08-17T18:56:18.567412", // string, isodate
  "table_of_contents_id": 1, // integer, TableOfContents.id
  "synthesis_id": 1, // integer, Synthesis.id
  "owner_id": 5, // integer, User.id
}
```

### `/discussions/`

- **GET**: a list of `Discussion` objects.

### `/discussions/<discussion_id>/`

- **GET**: a `Discussion` object with the matching `discussion_id`.



Posts
-------------------------------------------------------------------------------

A `Post` object takes the following form:

```json
{
  "id": 15, // integer
  "ancestry": "1,4,13,14," // string, ids of ancestors
  "parent_id": 14, // integer, Post.id
  "content_id": 15, // integer, Content.id
  "content": {}, // object, Content.serializable()
}
```


### `/discussions/<discussion_id>/root-posts/`

- **GET**: a list of `Post` objects related to the `Discussion` in descending
  order by the age of each post's youngest descendant. 

  *Options*
  - `limit`: integer. Limit the number of posts returned. Defaults to `20`.
  - `offset`: integer. Offset the set of posts returned by a specific amount.
  - `include_content`: boolean [true]. Whether each post should include its
    content.

- **POST**: Send a message to the source(s) of discussion. Requires
  authentication.

  *Required*
  - `message`: string.

### `/discussions/<discussion_id>/posts/<post_id>/`

- **GET**: a `Post` object with the matching `post_id`.

### `/discussions/<discussion_id>/posts/<post_id>/responses/`

- **GET**: a list of `Post` objects that are in response to the `Post` with an
  id matching `post_id` in descending order by the age of the content of each
  post's youngest descendant.

  *Options*
  - `limit`: integer. Limit the number of posts returned. Defaults to `20`.
  - `offset`: integer. Offset the set of posts returned by a specific amount.

- **POST**: Send a response to the post with an id matching `post_id`.
  Requires authentication.

  *Required*
  - `message`: string.

### `/discussions/<discussion_id>/posts/<post_id>/descendants/`

- **GET**: A list of `Post` objects that are descendents of the `Post` with an
  `id` matching `post_id` in descending order of the creation date of their 
  respective contents.

  *Options*
  - `limit`: integer. Limit the number of `Post` objects returned. Defaults to
    `20`.
  - `offset`: integer. Offset the set of `Post` objects returned by a specific
    amount.



Extracts
-------------------------------------------------------------------------------



### `/discussions/<discussion_id>/extracts/`

- **GET**: A list of `Extract` objects related to the `Discussion` which are
  owned by the authenticated `User`. Requires authentication.

- **POST**: Create an `Extract` from a `Post`.

  *Required*
  - `body`: string. The `body` of the `Extract`.
  - `source_id`: integer. The `id` of the `Content` from which the `Extract`
    came.

  *Optional*
  - `idea_id`: integer. The `id` of the `Idea` that the `Extract` should be
    attached to.
  - `order`: float. The `order` is a floating point number used to keep track
    of where an `Extract` should appear in a list. A good way to use this field
    is to take the difference between the `order` values on the object above
    and below, divide it by 2 and add it to the value of the lower object.

### `/discussions/<discussion_id>/extracts/<extract_id>/`

- **GET**: Get an `Extract` with the matching `extract_id`.

- **PUT**: Save an `Extract` with a specific `extract_id`.

- **DELETE**: Delete an `Extract` with a specific `extract_id`.



Ideas
-------------------------------------------------------------------------------

### `/discussions/<discussion_id>/ideas/`

- **GET**: A list of `Ideas` related to the `Discussion`.

- **POST**: Create an `Idea` related to the `Discussion`.

  *Required*
  - `long_title`: string. A long title for the `Idea`.

  *Optional*
  - `short_title`: string. A short title for the `Idea`.

### `/discussions/<discussion_id>/ideas/<idea_id>/

- **GET**: Get an `Idea` with the matching `idea_id`.

- **PUT**: Save an `Idea` with a specific `idea_id`.

### `/discussions/<discussion_id>/ideas/<idea_id>/relevant-posts/`

- **GET**: Get a list of `Post` objects related to the matching `idea_id`.

  *Options*
  - `limit`: integer. Limit the number of posts returned. Defaults to `20`.
  - `offset`: integer. Offset the set of posts returned by a specific amount.



Synthesis
-------------------------------------------------------------------------------

### `/discussions/<discussion_id>/syntheses/`

- **GET**: Get a list of `Synthesis` objects related to the `Discussion`.

### `/discussions/<discussion_id>/syntheses/<synthesis_id>`

- **GET**: Get a `Synthesis` object with an `id` matching `synthesis_id`.

- **PUT**: Save a `Synthesis` object with an `id` matching `synthesis_id`.

  *Required*
  - `subject`: string. A short subject line.
  - `introduction`: string. An introduction.
  - `conclusion`: string. A conclusion.
