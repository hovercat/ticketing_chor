create table post_tokens
(
    pt_id   serial constraint post_tokens_pk primary key,
    token varchar,
    token_time  timestamp default CURRENT_TIMESTAMP,
    what_for    varchar,
    used    bool
);

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


