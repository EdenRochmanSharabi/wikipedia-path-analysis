alter session set container=XEPDB1;
select owner, count(*) from all_tables where owner not in ('SYS','SYSTEM','OUTLN','AUDSYS','CTXSYS','DVSYS','LBACSYS','MDSYS','XDB') group by owner;
