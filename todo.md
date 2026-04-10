# Some kind of todo

## [ ] Add formatting options to text

Formatting data can be fetched via "format_data" field

```json
{
    "_": "Event",
    "format_data": "{\"version\":\"1\",\"items\":[{\"type\":\"italic\",\"offset\":19,\"length\":29},{\"type\":\"bold\",\"offset\":50,\"length\":46},{\"type\":\"italic\",\"offset\":100,\"length\":28},{\"type\":\"bold\",\"offset\":131,\"length\":10}]}"
}
```

```python
class FormattingDataVer1(pydantic.BaseModel):
    class FormattingTextType(enums.Enum):
        ITALIC = "italic"
        BOLD = "bold"
        UNDERLINE = "underline"
        URL = "url"
    offset: int
    length: int
    text_type: FormattingTextType = pydantic.Field(alias="type")
    url: typing.Optional[str] = None
    """only when type is URL"""

```

## [ ] Share message via inline button

with updating for 5 minutes
