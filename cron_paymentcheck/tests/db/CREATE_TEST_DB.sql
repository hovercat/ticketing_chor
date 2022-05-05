SET search_path TO ticketing;

DROP TABLE IF EXISTS transaction;
DROP TABLE IF EXISTS reservation;
DROP TABLE IF EXISTS concert;
DROP TABLE IF EXISTS reservation_status;
DROP TABLE IF EXISTS payment_status;
DROP TABLE IF EXISTS reservation_payment_status;

DROP SCHEMA IF EXISTS ticketing;
CREATE SCHEMA ticketing;

SET search_path TO ticketing;

create table concert
(
    concert_id           serial
        constraint concert_pk
            primary key,
    date_sale_start      date,
    date_sale_end        date,
    date_concert         date,
    concert_title        varchar,
    concert_location     varchar,
    full_price           real,
    student_price        real,
    duration_reminder    integer,
    duration_cancelation integer,
    tickets_available    integer
);

alter table concert
    owner to postgres;

create unique index concert_concert_id_uindex
    on concert (concert_id);

create table reservation_status
(
    rs_id  integer not null
        constraint reservation_status_pk
            primary key,
    status varchar
);

alter table reservation_status
    owner to postgres;

create unique index reservation_status_rs_id_uindex
    on reservation_status (rs_id);

create table payment_status
(
    ps_id  integer not null
        constraint payment_status_pk
            primary key,
    status varchar
);

alter table payment_status
    owner to postgres;

create unique index payment_status_ps_id_uindex
    on payment_status (ps_id);

create table reservation_payment_status
(
    rps_id integer not null
        constraint reservation_payment_status_pk
            primary key,
    status varchar
);

alter table reservation_payment_status
    owner to postgres;

create table reservation
(
    res_id                   serial
        constraint reservation_pk
            primary key,
    concert_id               integer
        constraint reservations_concert_concert_id_fk
            references concert,
    user_email               varchar not null,
    user_name                varchar not null,
    tickets_full_price       integer default 0,
    tickets_student_price    integer default 0,
    payment_reference        varchar,
    date_reservation_created date    default CURRENT_DATE,
    date_email_activated     date,
    date_reminded            date,
    status                   varchar,
    pay_state                varchar
);

alter table reservation
    owner to postgres;

create table transaction
(
    transaction_id      serial
        constraint transaction_pk
            primary key,
    payment_reference   varchar,
    currency            varchar,
    amount              real,
    debtor_iban         varchar,
    debtor_name         varchar,
    payment_date        date,
    res_id              integer
        constraint transaction_reservation_res_id_fk
            references reservation,
    bank_transaction_id varchar,
    status              varchar
);

alter table transaction
    owner to postgres;

create unique index reservation_payment_status_rps_id_uindex
    on reservation_payment_status (rps_id);

