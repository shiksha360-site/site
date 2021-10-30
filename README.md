# site

Site source code

**You likely want KalamAcademy/data if you want to contribute to the actual data**

### Usage

1. Clone KalamAcademy/data inside this repo
2. Either restore from backup or load ``sdk/schema.sql`` to a PostreSQL 14 database named ``kalam`` (``\c kalam`` and then ``\i sdk/schema.sql``)
3. Bulld shiksdk from sdk/shiksdk
3. Run shiksdk devserver to run the devserver. Go to http://127.0.0.1:8000 and run /data/build
4. Setup nginx using nginx-cfg.conf as per the comments inside it