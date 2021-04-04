Monthly Music
====
Overview
----
This script is used to look at a set of users' most listened to tracks, over the past month, on Spotify, and compile them into a playlist for them. It also uses these monthly listening habits to generate a set of recommended songs for the user this month.

The criteria for selecting a user's recommendations could likely be significantly improved. The current approach taken revolves around taking the two most common genres from the user's past month's top songs, as well as the three top songs, and providing those as seeds for Spotify's recommendations, while also filtering using the 25th and 75th percentile values for their top songs' danceability, energy, valence and tempo.

Each playlist will also have an image generated to accompany it, consisting of three album covers featured in it, its colour scheme based upon the images featured in it.

![Playlist Preview](/preview.png)

How to Use
----
Once you have a copy of this script, you will need to either create a copy of config_example.json named config.json, or just rename the file, and fill it out as follows:
- _client\_id_, the client id of your Spotify Development App
- _client\_secret_, the client secret key of your Spotify Development App
- _redirect\_uri_, the redirect URI of your Spotify Development App
- _controller\_username_, the Spotify username of the account which you wish for all of these playlists to be hosted on
- _usernames_, any number of Spotify usernames of accounts which you wish to create these playlists for
If you do not know any of the above information, the Spotify development website should help you to understand where to find them.

Once your configuration file is set up correctly, you should run the script, and it should ask you to authenticate each of the accounts that are listed in your configuration, including the controller file. For the smoothest experience, with actually authenticating Spotify accounts from the web, I recommend that you deal with just one account at a time.

At this point, you should be able to run the script and find that it generates the playlists detailed, on the controller account.

Issues
----
There are a few known or suspected issues and limitations of this script.
- The Spotify API does not tell us anything about whether a user has listened to a track or not, and so the recommendations are only able to rule out the users' top tracks, and tracks that they have in playlists
- The request rate limitations have not been tested, and it is not known how this script will cope with many users - thus far it has only been used with two users
- The authentication process (which will need to be carried out for both the control account and any accounts being looked at) is not embedded within the script in any way, and will just take you to a web page
- The image generation is dependent on ArialBold.ttf being found where expected, and will likely face issues if it is not found there - I am only sure of its location on my own Windows 10 machine, and assume it will be the same on other standard Windows 10 builds

Future Work
----
The future work planned for this project (though with no certain timeline) involves making it more available as a service. It's intended that the authentication process will be pulled apart, into something which can be handled via a web page, so that the functionality may be made available online, with users being able to include themselves, as opposed to having to be added through the current, manual process.