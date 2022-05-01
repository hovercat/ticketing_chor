create table if not exists concert
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
    duration_cancelation integer
);

alter table concert
    owner to postgres;

create unique index if not exists concert_concert_id_uindex
    on concert (concert_id);

create table if not exists reservations
(
    res_id                   serial
        constraint reservations_pk
            primary key,
    concert_id               integer
        constraint reservations_concert_concert_id_fk
            references concert,
    user_email               varchar,
    user_name                varchar,
    tickets_full_price       integer default 0,
    tickets_student_price    integer default 0,
    payment_reference        varchar,
    date_reservation_created date,
    date_paid                date,
    finalized                boolean default false,
    canceled                 boolean default false
);

alter table reservations
    owner to postgres;

create unique index if not exists reservations_res_id_uindex
    on reservations (res_id);


