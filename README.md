# sgchemist

![Build status](https://github.com/PoloB/sgchemist/actions/workflows/ci.yml/badge.svg)

An Object Relation Mapper for Autodesk Flow Production Tracker (previously Shotgrid and Shotgun) inspired by SQLAlchemy.


## Declaring entities

You can declare all the entities and fields using a dataclass like structure:

```python
from __future__ import annotations

from sgchemist.orm import SgEntity 
from sgchemist.orm import TextField 
from sgchemist.orm import EntityField
from sgchemist.orm import MultiEntityField
from sgchemist.orm import mapped_field


class Project(SgEntity):
    __sg_type__ = "Project"
    
    name: TextField = mapped_field(name="code")
    title: TextField
    assets: MultiEntityField[list[Asset]]
    
    
class Asset(SgEntity):
    __sg_type__ = "Asset"

    name: TextField = mapped_field(name="code")
    description: TextField
    project: EntityField[Project]

```

## Query building

To make a query using sgchemist, you need to use two elements:
* an engine: responsible for communicating with your Shotgrid instance.
`sgchemist` provides an engine implementation using the `shotgun-api3`.
* and a session: responsible for converting raw data from the engine back to objects.
In case of creation and update querying it also implements the unit of work pattern.

```python

from shotgun_api3 import Shotgun
from sgchemist.orm import ShotgunAPIEngine
from sgchemist.orm import select
from sgchemist.orm import Session

from myentities import Asset

# Create the engine
shotgun = Shotgun("https://mysite.shotgunstudio.com", script_name="xyz", api_key="abc")
engine = ShotgunAPIEngine(shotgun)

# Create the session
session = Session(engine)

# Create the query
query = select(Asset).where(Asset.project.name.eq("myproject"))

# Perform the query using the session
assets = list(session.exec(query))

# Update the description of the assets
with session:
    for asset in assets:
        asset.description = "This is an awesome asset"
        session.add(asset)
# Assets are now updated
```
