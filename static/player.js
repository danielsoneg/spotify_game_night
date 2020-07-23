window.onSpotifyWebPlaybackSDKReady = async () => {
    const player = new Spotify.Player({
      name: 'Game Night',
      getOAuthToken: async cb => { 
        const token_resp = await fetch("/token", {"redirect":"manual"})
        if (!token_resp.ok){ window.location = "/"; }
        const token = await token_resp.text()
        cb(token); }
    });

    // Error handling
    player.addListener('initialization_error', ({ message }) => { console.error(message); });
    player.addListener('authentication_error', ({ message }) => { console.error(message); });
    player.addListener('account_error', ({ message }) => { console.error(message); });
    player.addListener('playback_error', ({ message }) => { console.error(message); });

    function get_track(state) {
      return state.track_window.current_track;
    }

    function track_title(current_track) {
      name = current_track.name;
      artist = current_track.artists[0].name;
      return `${artist} - ${name}`;
    }

    function album_art(current_track) {
      return current_track.album.images[1].url;
    }
    const title = document.getElementById("title")
    const art = document.getElementById("art")
    const volSlider = document.getElementById("volume")
    const volValue = document.getElementById("volval")
    title.innerText = "Waiting..."
    // Playback status updates
    player.addListener('player_state_changed', state => { 
      console.log(state);
      current_track = get_track(state);
      console.log(track_title(current_track));
      title.innerText = track_title(current_track);
      art.src = album_art(current_track);
      
    });

    // Ready
    player.addListener('ready', ({ device_id }) => {
      console.log('Ready with Device ID', device_id);
    });

    // Not Ready
    player.addListener('not_ready', ({ device_id }) => {
      console.log('Device ID has gone offline', device_id);
    });

    volSlider.onchange = () => {
      player.setVolume(volSlider.value / 100).then(() => {
        player.getVolume().then(volume => {
          let volume_percentage = volume * 100;
          console.log(`The volume of the player is ${volume_percentage}%`);
          volValue.innerText = volume_percentage;
        });
      });
    }

    // Connect to the player!
    player.connect();
  };