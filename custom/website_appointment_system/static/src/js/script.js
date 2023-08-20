odoo.define('website_appointment_system.was', function (require) {
    "use strict";

    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');
    publicWidget.registry.appointment = publicWidget.Widget.extend({
        selector: '#appointment',
        events: {
            'blur #user': '_slots_time_date',
            'blur #date_app': '_slots_time_date',
            'blur #desg': '_users_as_desg',
            'change .user_cal': '_cal_slots_time_date',
            'change #client_name_bool': 'client_name_bool',
            'click .prev_month': 'prev_month',
            'click .next_month': 'next_month',
            'click .o_day': '_o_day_events',
        },

        client_name_bool: function (e) {
            if (e.currentTarget.checked) {
                $('#client_name').removeClass('d-none');
            }
            else {
                $('#client_name').val('');
                $('#client_name').addClass('d-none');
            }
        },

        select_slot: function (e) {

            $.ajax({
                type: "POST",
                dataType: 'http',
                url: '/appointment',
                data: { 1: 1 },
            });
        },

        _o_day_events: function (e) {
            $('.o_day').removeClass('bg-primary');
            $(e.currentTarget).addClass('bg-primary');
            var date = $(e.currentTarget).data('date');
            var re_sch_invoice_id = $('#re_sch_invoice_id').val();
            var user_id = $(e.currentTarget).data('user_id');
            var appointment_type_id = $(e.currentTarget).data('appointment_type_id');

            ajax.jsonRpc("/o_day_events", 'call', {
                'user_id': user_id,
                'date': date,
                'appointment_type_id': appointment_type_id,
            }).then(function (data) {
                if (data) {
                    $('#view_slots_title').text(data[0][2] + ' with ' + data[0][0] + ' (' + data[0][1] + ')')
                    $("#view_slots").html(` <div class="h3 text-center w-100 alert alert-info">Select a time slot to proceed...</div>`)
                    data.shift();
                    $('.slot_ele').remove();
                    data.forEach(function (value, index, array) {
                        var div_ele = document.createElement("div");
                        div_ele.setAttribute("class", "col-lg-3 d-flex col-md-3 col-sm-3 p-1 slot_ele text-center");
                        div_ele.setAttribute("data-slot_id", value[0]);
                        div_ele.innerHTML = `<a  href='/appointment?slot_id=${value[0]}&user__id=${user_id}&date=${date}&appointment_type_id=${appointment_type_id}&re_sch_invoice_id=${re_sch_invoice_id}' class='border m-auto py-1 px-2 border-primary cp h_over rounded'>${value[1]}</a>`;
                        $('#view_slots')[0].appendChild(div_ele);
                    });
                }
            });
        },

        _cal_slots_time_date: function (e) {
            var user = e.currentTarget.value;
            console.log("USER", user)
            if (user) {
                $('#submit_user').removeAttr('disabled');
                ajax.jsonRpc("/find_types", 'call', {
                    'user_id': user,
                }).then(function (data) {
                    if (data) {
                        $('#appointment_type_id').find('option').not(':first').remove();
                        data.forEach(function (value, index, array) {
                            $('#appointment_type_id').append(`<option value=${value[0]}>${value[1]}</option>`);
                        });
                    }
                });
            }
            else {
                $('.user_cal').css('border', '1px solid red');
            }
        },

        prev_month: function (e) {
            $(e.currentTarget).parent('.app_calendar').prev('.app_calendar').removeClass('d-none');
            if ($(e.currentTarget).parent('.app_calendar').prev('.app_calendar')[0]) {
                $(e.currentTarget).parent('.app_calendar').addClass('d-none');
            }
        },

        next_month: function (e) {
            $(e.currentTarget).parent('.app_calendar').next('.app_calendar').removeClass('d-none');
            if ($(e.currentTarget).parent('.app_calendar').next('.app_calendar')[0]) {

                $(e.currentTarget).parent('.app_calendar').addClass('d-none');
            }
        },

        _users_as_desg: function (e) {
            var desg = e.currentTarget.value;

            if (desg) {
                ajax.jsonRpc("/users_as_desg", 'call', {
                    'desg': desg,

                }).then(function (data) {
                    if (data) {
                        $('#user').find('option').not(':first').remove();
                        data.forEach(function (value, index, array) {
                            $('#user').append(`<option value=${value[0]}>${value[1]}</option>`);
                        });
                    }
                });
            }
        },
        _slots_time_date: function (e) {
            var date_value = $('#date_app').val();
            var user = $('#user').val();

            if (!user) {
                $('#user').css('border', '1px solid red');
            }
            else {
                ajax.jsonRpc("/location_as_user", 'call', {
                    'user_id': user,
                }).then(function (data) {
                    if (data) {
                        $('#additional_info').removeClass('d-none');
                        $('#amount_text').text(data[1]);
                        $('#address_text').text(data[0]);
                    }
                });
            }
            if (date_value && user) {
                ajax.jsonRpc("/slots_time_date", 'call', {
                    'date_app': date_value,
                    'user_id': user,
                }).then(function (data) {
                    if (data) {
                        $('#slot_time').find('option').not(':first').remove();
                        data.forEach(function (value, index, array) {
                            $('#slot_time').append(`<option value=${value[0]}>${value[1]}</option>`);
                        });
                    }
                });
            }
        },

    });
});