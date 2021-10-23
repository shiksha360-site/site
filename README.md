# site

Site source code

**You likely want KalamAcademy/data if you want to contribute to the actual data**

### Usage

1. Clone KalamAcademy/data inside this repo
2. Either restore from backup or load ``sdk/schema.sql`` to a PostreSQL 14 database named ``kalam`` (``\c kalam`` and then ``\i sdk/schema.sql``)
3. Run manage.py to run the internal tool. Run /data/build
4. Setup nginx using nginx-cfg.conf as per the comments inside it