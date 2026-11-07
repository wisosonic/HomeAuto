// Plain-language description of each sensor kind, shown on the Sensors page.
// Keyed by the backend's sensor `kind`. For a new sensor, add an entry here.
//   summary: what it is / why it is useful (always visible)
//   gives:   exactly what information it reports (and what it does NOT)
//   goodFor: example automations
//   notes:   limits and practical tips

export const SENSOR_INFO = {
  motion: {
    model: "PIR HC-SR501",
    summary:
      "Detects movement of warm bodies (people, pets) in front of it by sensing changes in infrared heat.",
    gives:
      "A simple on/off signal: motion detected or not. It stays on for a few seconds after the last movement (hold time is set with a pot on the board). It does not tell distance, direction or how many people.",
    goodFor: "Presence-based lighting, intruder alerts, knowing if a room is occupied.",
    notes:
      "Needs 30-60 s to settle after power-up, so early triggers are normal. Can false-trigger near heaters, vents or direct sunlight. Range is roughly 3-7 m, adjustable on the board.",
  },
  sound: {
    model: "Microphone module (LM393)",
    summary: "Detects when the noise level around it goes above a threshold, such as a clap, a bark or a slammed door.",
    gives:
      "An on/off signal: loud sound detected or not. It does not measure loudness or recognise what the sound is, because the analog output is not usable on the Pi.",
    goodFor: "Clap switch, noise or break-in alert, waking another automation.",
    notes:
      "Set the trigger level with the blue pot on the board. It reacts to short loud bursts, not to a steady quiet hum.",
  },
  flame: {
    model: "IR flame sensor",
    summary: "Senses the infrared light that flames give off, so it can warn about fire near it.",
    gives:
      "An on/off signal: flame (IR source) detected or not. It does not give temperature or distance.",
    goodFor: "Early warning near a stove, heater or workshop.",
    notes:
      "Sunlight and incandescent bulbs also emit IR and can trigger it. Typical range is about 20-80 cm and depends on the pot setting. It is a hobby sensor, not a certified fire alarm: never rely on it for safety.",
  },
  obstacle: {
    model: "IR obstacle sensor (FC-51)",
    summary: "Sends out infrared light and checks if it bounces back, which tells if an object is right in front of it.",
    gives:
      "An on/off signal: object present within range or not (range ~2-30 cm, set with the pot). It does not measure the actual distance.",
    goodFor: "Door or drawer opening, mailbox, counting items passing, proximity triggers.",
    notes:
      "Black or matte surfaces reflect poorly and may be missed. Bright sunlight can interfere, so use it indoors or shaded.",
  },
  rain: {
    model: "Rain / water sensor (MH-RD)",
    summary: "Detects water drops on its sensing plate: wet versus dry.",
    gives:
      "An on/off signal: wet or dry, based on a threshold set with the pot. It does not measure how much rain has fallen.",
    goodFor: "Rain alert, reminder to close a window or bring laundry in, simple leak detection.",
    notes:
      "The plate corrodes if constantly powered and wet, so dry it after use. Mount it at an angle so drops run off and it can dry.",
  },
  vibration: {
    model: "Vibration / shock switch",
    summary: "Detects knocks, shocks and vibration using a small spring switch.",
    gives:
      "An on/off signal that pulses when the module is shaken. It does not tell how strong the vibration is or its direction.",
    goodFor: "Tamper or knock alerts on a door or box, detecting that an appliance is running.",
    notes:
      "Very sensitive. One knock can produce several quick changes, so the software debounces them into one event. Its behaviour depends on the exact module, so check it on the real hardware.",
  },
};

const FALLBACK = {
  model: "",
  summary: "Digital on/off sensor.",
  gives: "An on/off signal reporting whether it currently detects something.",
  goodFor: "",
  notes: "",
};

export const sensorInfo = (kind) => SENSOR_INFO[kind] ?? FALLBACK;
