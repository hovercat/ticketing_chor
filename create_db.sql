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
    date_reservation_created date,
    finalized                boolean default false,
    canceled                 boolean default false,
    date_email_activated     date
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
    handled             boolean default false,
    bank_transaction_id varchar
);

alter table transaction
    owner to postgres;

create view open_reservations
            (res_id, concert_id, user_email, user_name, tickets_full_price, tickets_student_price, payment_reference,
             date_reservation_created, finalized, canceled, date_email_activated)
as
SELECT res.res_id,
       res.concert_id,
       res.user_email,
       res.user_name,
       res.tickets_full_price,
       res.tickets_student_price,
       res.payment_reference,
       res.date_reservation_created,
       res.finalized,
       res.canceled,
       res.date_email_activated
FROM ticketing.reservation res
WHERE NOT res.finalized
  AND NOT res.canceled;

alter table open_reservations
    owner to postgres;

create view concerts_info
            (concert_id, concert_title, date_concert, "Pending Tickets", "Reservable Tickets", "Sold Tickets",
             "Unsold Tickets") as
SELECT conc.concert_id,
       conc.concert_title,
       conc.date_concert,
       sum(res_open.tickets_full_price) + sum(res_open.tickets_student_price)                        AS "Pending Tickets",
       conc.tickets_available - COALESCE(sum(res_open.tickets_full_price) + sum(res_open.tickets_student_price),
                                         0::bigint)                                                  AS "Reservable Tickets",
       COALESCE(sum(res_final.tickets_full_price) + sum(res_final.tickets_student_price), 0::bigint) AS "Sold Tickets",
       conc.tickets_available -
       COALESCE(sum(res_final.tickets_full_price) + sum(res_final.tickets_student_price), 0::bigint) AS "Unsold Tickets"
FROM ticketing.concert conc
         LEFT JOIN ticketing.reservation res_open
                   ON conc.concert_id = res_open.concert_id AND NOT res_open.canceled AND NOT res_open.finalized
         LEFT JOIN ticketing.reservation res_final
                   ON conc.concert_id = res_final.concert_id AND NOT res_final.canceled AND res_final.finalized
GROUP BY conc.concert_id, conc.concert_title, conc.date_concert;

alter table concerts_info
    owner to postgres;


