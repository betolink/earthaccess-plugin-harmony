# earthaccess-harmony

Subset and transform Earthdata granules with NASA
[Harmony](https://harmony.earthdata.nasa.gov/), through the earthaccess plugin
contract.

```python
import earthaccess

results = earthaccess.search_data(
    short_name="ATL06",
    bounding_box=(-120, 40, -110, 45),
)

job = earthaccess.plugins.harmony.request(
    results,
    bbox=(-120, 40, -110, 45),
    variables=["/gt1l/land_ice_segments/h_li"],
    skip_preview=True,
)
assets = job.results()
```

## Contract

- `output = "assets"`, `auth = "edl"`, `needs = {"concept_id"}`.
- Remote, resumable job: `earthaccess.plugins.harmony.get_job(job.id)`.
- Capabilities: `cancel`, `pause`, `resume`; Harmony-specific `skip_preview()`.
- A large request enters the preview state, which maps to `PAUSED`.

## Verification points

`src/earthaccess_harmony/client.py` isolates every unverified `harmony-py`
detail (client construction, `Request` keywords). `job.py:STATUS_MAP` is the
single place to fix Harmony's status strings.

## License

MIT.
