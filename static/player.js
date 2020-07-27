window.onSpotifyWebPlaybackSDKReady = async () => {
    const player = new Spotify.Player({
      name: 'Game Night',
      getOAuthToken: async cb => { 
        const token_resp = await fetch("/token", {"redirect":"manual"})
        if (!token_resp.ok){ console.log(token_resp); await new Promise(r => setTimeout(r, 2000)); window.location = "/"; }
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

    function album_art(current_track, i=1) {
      return current_track.album.images[i].url;
    }
    const title = document.getElementById("title")
    const artist = document.getElementById("artist")
    const art = document.getElementById("art")
    const volSlider = document.getElementById("volume")
    const volLabel = document.getElementById("vollabel")
    const bg = document.getElementById("background")
    title.innerText = "Waiting for next song..."
    // Playback status updates
    player.addListener('player_state_changed', state => { 
      console.log(state);
      current_track = get_track(state);
      title.innerText = current_track.name;
      artist.innerText = current_track.artists.map(a => a.name).join(", ");
      art.src = album_art(current_track);
      bg.style.backgroundImage = `url(${album_art(current_track,2)})` 
    });

    // Ready
    player.addListener('ready', ({ device_id }) => {
      console.log('Ready with Device ID', device_id);
      window.onbeforeunload = () => { fetch("/logout"); }
    });

    // Not Ready
    player.addListener('not_ready', ({ device_id }) => {
      console.log('Device ID has gone offline', device_id);
    });

    volSlider.onchange = () => {
      player.setVolume(volSlider.value / 100).then(() => {
        player.getVolume().then(volume => {
          let volume_percentage = `${volume * 100}%`;
          console.log(`The volume of the player is ${volume_percentage}`);
          if (volume > .7) { volLabel.innerText = "🔊" } else if (volume > .35) { 
            volLabel.innerText = "🔉"
          } else if (volume > 0) {
            volLabel.innerText = "🔈"
          } else { volLabel.innerText = "🔇"}
        });
      });
    }

    // Connect to the player!
    player.connect();
  };