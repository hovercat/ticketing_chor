DROP database choir_ticketing;
DROP SCHEMA ticketing CASCADE;
COMMIT;

CREATE database choir_ticketing;
CREATE SCHEMA ticketing;

SET search_path TO ticketing,public;

create table concert
(
    concert_id           serial
        constraint concert_pk
            primary key,
    date_sale_start      timestamp,
    date_sale_end        timestamp,
    date_concert         timestamp,
    concert_title        varchar,
    concert_location     varchar,
    full_price           real,
    student_price        real,
    duration_reminder    integer,
    duration_cancelation integer,
    total_tickets        integer
);

alter table concert
    owner to postgres;

create unique index concert_concert_id_uindex
    on concert (concert_id);

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
    date_reservation_created timestamp    default CURRENT_TIMESTAMP,
    date_email_activated     timestamp,
    date_reminded            timestamp,
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




INSERT INTO concert (concert_id, date_sale_start, date_sale_end, date_concert, concert_title, concert_location, full_price, student_price,
                     duration_reminder, duration_cancelation, total_tickets)
VALUES
    (1, '2022-05-17', '2022-06-22', '2022-06-24 19:00', 'Can’t stop the Feeling', 'Informatikhörsaal; Treitlstraße 3, 1040 Wien', 15, 5, 7, 14, 300);

COMMIT;
