# Wheretolive ... ?

![Test and Deploy](https://github.com/kelvinn/wheretolive/workflows/Test%20and%20Deploy/badge.svg)

### Loading Data

#### Transport

```bash
shp2pgsql -I shapes.shp transport | psql -h localhost -U postgres -d wheretolive
```

#### OSM

```bash
osm2pgsql NSW.xml -d wheretolive -U postgres -P 5432 --hstore

```

#### School Catchments

```bash
shp2pgsql -I catchments.shp catchments | psql -U postgres -d wheretolive
```


