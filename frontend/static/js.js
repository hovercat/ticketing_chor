var price_student = price_full = seats_left = 0;
$(document).ready(function() {
    price_student = parseFloat($('#pl_student').text());
    price_full = parseFloat($('#pl_full').text()); //storing price in global vars prepares us for dynamic updating later
    $('.ticket-amount').on('change', updateTotal);
    $('#sendreservation').prop("disabled", true);
    updateTotal();
    updateSeatsLeft();
});

function updateSeatsLeft() {
    var selected_concert = parseInt($('#concertdate').val());
    $.ajax({
        url: "getseats/"+selected_concert,
        type: "GET",
        dataType:"json",
        success: function(data) {
            console.log(data);
            if(!data.failed) {
                seats_left = data.seats;
                $('#tickets_left').val("asdf")
            }
        }
    });
    setTimeout(updateSeatsLeft, 5000);
}

function updateTotal() {
    //Also we don't want to do an ajax query everytime number of tickets is changed
    var n_student = parseInt($('#tickets_student').val());
    var n_full = parseInt($('#tickets_full').val());
    n_full = isNaN(n_full) ? 0 : n_full;
    n_student = isNaN(n_student) ? 0 : n_student;
    var total_tickets = n_full + n_student;
    if(total_tickets > 0 || total_tickets > seats_left) {
        //TODO: Add here some notification if its too many seats
        $('#sendreservation').prop("disabled", false);
    } else {
        $('#sendreservation').prop("disabled", true);
    }

    //var total = n_student*price_student+n_full*price_full;
    let eurDElocale = Intl.NumberFormat('de-DE',{
        style: 'currency',
        currency: 'EUR'
    });
    var total = n_student*pl_student + n_full*pl_full;
    $('#total').text(eurDElocale.format(total));
};

