// function ajax_submit(msg_selector, form_name) {
//   var valuesToSubmit = $('form[name=' + form_name + ']').serialize();
//   $.ajax({
//     type: "PUT",
//     url: "/votes", //submits it to the given url of the form
//     data: valuesToSubmit,
//     dataType: "JSON", // you want a difference between normal and ajax-calls, and json is standard
//   }).done(function(){
//     msg = "saved";
//     saved_messages_shown++;

//     if (saved_messages_shown >= wacky_message_threshold) {
//       msg = success_messages[Math.floor(Math.random() * success_messages.length)];
//     }

//     flash_element(msg_selector, msg);
//   }).fail(function(){
//     flash_element(msg_selector, "failed");
//   });

//   return false; // prevents normal behaviour
// }

function load_light_names() {
  $.ajax({
    type: 'GET',
    url: '/list_lights',
    dataType: 'json',
    success: function(lights) {
      for (var i = 0; i < lights.length; i++) {
        $('#lightSelect')
          .append(
            '<option value="' + lights[i] + '">' + lights[i] + '</option>');
      }
    }
  })
}

function load_presets() {
  $.ajax({
    type: 'GET',
    url: '/list_presets',
    dataType: 'json',
    success: function(presets) {
      for (var i = 0; i < presets.length; i++) {
        $('#preset-list')
          .append(
              '<button type="button" class="btn btn-secondary" name="button"' +
              'onclick="activate_preset(&quot;' + presets[i] + '&quot;)">' + 
              presets[i] + '</button>');
      }
    }
  })
}

function load_values() {
  load_light_names();
  load_presets();
}

function activate_preset(name) {
  $.ajax({
    type: 'GET',
    url: '/activate_preset?name=' + name,
  })
}
