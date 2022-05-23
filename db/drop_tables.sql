
SET search_path TO ticketing,public;

drop table if exists post_tokens;
drop table if exists concert cascade;
drop table if exists reservation cascade;
drop table if exists transaction;

--truncate table concert CASCADE;
--truncate table reservation CASCADE;
--truncate table transaction;
commit;