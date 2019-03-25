// Populates the dropdown list of bulbs.
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

// Populates the button group of presets.
function load_presets() {
  $.ajax({
    type: 'GET',
    url: '/list_presets',
    dataType: 'json',
    success: function(presets) {
      for (var i = 0; i < presets.length; i++) {
        $('#preset-list')
          .append(
              '<button type="button" class="btn btn-primary" name="button"' +
              'onclick="activate_preset(&quot;' + presets[i] + '&quot;)">' +
              presets[i] + '</button>');
      }
    }
  });
}

// Returns the current light mode, either color or white
function get_mode() {
  return $('#modeSelect input:radio:checked').val();
}

function onColorInputStart(color) {
  userInteracting = true;

  // If the selected color has any s, then set mode to color.
  mode = get_mode();
  hsl = color.hsl;
  if (mode === 'white' && hsl.s !== 0) {
    $('#mode-color').click();
  }
}

function onColorInputEnd() {
  userInteracting = false;
}

function onColorChange(color, changes) {
  // Ignore changes not triggered by the user.
  if (!userInteracting) {
    return;
  }

  bulb = $('#lightSelect').val();
  if (bulb === '') {
    console.log('bulb not selected');
    return;
  }

  mode = get_mode();
  if (mode === 'color') {
    // Trim off '#'
    color = color.hexString.substring(1);
    $.ajax({
      type: 'GET',
      url: '/set_lights?bulb=' + bulb + '&rgbw=' + color + '00',
    });
  } else if (mode === 'white') {
    color = color.hsl.l;
    // Lightness is on a scale from 0-100, not 0x00-0xFF
    hex = Math.round(((color) / 100.0) * 255).toString(16);
    $.ajax({
      type: 'GET',
      url: '/set_lights?bulb=' + bulb + '&rgbw=000000' + hex,
    });
  } else {
    console.log('invalid mode:' + mode);
  }
}

function activate_preset(name) {
  $.ajax({
    type: 'GET',
    url: '/activate_preset?name=' + name,
  });
}

function set_power(onoff) {
  bulb = document.getElementById('lightSelect').value
  if (bulb === '') {
    console.log('bulb not selected');
    return;
  }
  $.ajax({
    type: 'GET',
    url: '/set_lights?bulb=' + bulb + '&power=' + onoff,
  });
}

var userInteracting = false;

function init() {
  load_light_names();
  load_presets();

  var colorPicker = new iro.ColorPicker('#color-picker-container', {
    wheelLightness: false,
  });
  colorPicker.on('color:change', onColorChange);
  colorPicker.on('input:start', onColorInputStart);
  colorPicker.on('input:end', onColorInputEnd);

  // Reset the color picker to 0% sat when the user selects whites mode so
  // the ui is less confusing.
  $('#modeSelect').change(function(ob) {
    if (get_mode() === "white") {
      curcolor = colorPicker.color.hsl;
      curcolor.s = 0;
      colorPicker.color.hsl = curcolor;
    }
    return true;
  });
}