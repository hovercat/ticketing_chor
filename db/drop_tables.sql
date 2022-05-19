
SET search_path TO ticketing,public;

--truncate table concert CASCADE;
truncate table reservation CASCADE;
truncate table transaction;
commit;