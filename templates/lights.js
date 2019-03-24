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
              '<button type="button" class="btn btn-primary" name="button"' +
              'onclick="activate_preset(&quot;' + presets[i] + '&quot;)">' +
              presets[i] + '</button>');
      }
    }
  })
}

function onColorInputStart(color) {
  mode = document.getElementById('modeSelect').value

  // If the selected color has any s, then set mode to color.
  hsl = color.hsl
  if (mode === 'white' && hsl.s !== 0) {
    // Change mode to color
    $('#modeSelect').val('color');
  }
}

function onColorChange(color, changes) {
  // print the color's new hex value to the developer console
  bulb = document.getElementById('lightSelect').value
  if (bulb === '') {
    return;
  }

  mode = document.getElementById('modeSelect').value

  if (mode === 'color') {
    color = color.hexString.substring(1);
    $.ajax({
      type: 'GET',
      url: '/set_lights?bulb=' + bulb + '&rgbw=' + color + '00',
    });
  } else if (mode === 'white') {
    color = color.hsl.l;
    hex = Math.round(((color) / 100.0) * 255).toString(16);
    $.ajax({
      type: 'GET',
      url: '/set_lights?bulb=' + bulb + '&rgbw=000000' + hex,
    });
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
    return;
  }
  $.ajax({
    type: 'GET',
    url: '/set_lights?bulb=' + bulb + '&power=' + onoff,
  });
}

function load_values() {
  load_light_names();
  load_presets();

  var colorPicker = new iro.ColorPicker('#color-picker-container', {
    wheelLightness: false,
  });
  colorPicker.on('color:change', onColorChange);
  colorPicker.on('input:start', onColorInputStart);
  $('#modeSelect').change(function(ob) {
    mode = document.getElementById('modeSelect').value
    if (mode === "white") {
      // Reset the colorpicker to 0% sat for whites.
      curcolor = colorPicker.color.hsl;
      curcolor.s = 0;
      colorPicker.color.hsl = curcolor;
    }
    return true;
  });
}