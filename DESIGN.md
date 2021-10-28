# Objective

People right now have to look through Youtube and other sites to find good videos which are often wrong and not the best way to learn. Kalam Academy (now shiksha360) tries to fix this by:

- Providing the best sources to learn from so students can just focus on learning
- Create a study plan to set students up for success as per the CBSE etc. syllabus (showing the best interactive/whiteboard video, experiment, resources to explore more on a topic)
- Crowdsource other resources and provide high quality experiments such as PhET

While not an objective, having all of this information freely available for others to use (such as a JSON of the entire NCERT syllabus to make it easier for others to use) is a possible extra thing.

## Requirements

- Some way of getting the syllabus (this will be done manually for now)
- A way to find videos for a subject given a topic/subtopic
- A way to store this information and actually use it in the site
- A interactive video, whiteboard video and experiment (QA can also be done)

# High Level Design

## Storage

The entire syllabus will be stored in the ``data`` repository as YAML files. YAML was chosen as it was simple (a database was not needed and data can easily be backed up and stored), easier to debug (we can directly edit the YAML files instead of going through the database and then modifying it using SQL/pgAdmin etc) and because it allowed comments (unlike JSON) and potentially unstructured data.

Ultimately, this data is 'compiled' from YAML into msgpack. Ramuel.yaml is used to do this.

We still do not have a solution to automate getting the syllabus or create the keywords/tags from the syllabus yet. This is currently done manually (see [Low Level Design](#low-level-design)).

## Current Process
The script currently loops through all the YAML files, fixes the output if there are any missing/blank fields. A 'keystone' folder is also created to house data that is **key** to the site but is **not** something that is part of the actual problem or solution (example being Table of Contents, team information, language information, information about boards, information about extra sources, some precompiled HTML etc)

## Internal Tool
We have an internal tool (right now FastAPI+Swagger 4.0 so we don't have to code the UI for our admin tool ourselves) to make adding of the syllabus/topics/videos easier along with the videos associated with it.

## Future Ideas

### Scraping 
For every topic in each grade, we could have a script that loops through these topics, parses them and then give each topic + subtopic to the master scraper. The master scraper goes through the list of scrapers and runs them. Each scraper gets access to the youtube api, channel info (for youtube), chapter info, subtopic and the "scrape cache". The chapter info also contains the grade, subject and board information. 

Using accept and reject keywords found in the chapter info, the scraper can then uses either youtubes api (or any other potential site we may add support for) to first find the playlist (in the case of youtube) and the actual video (youtube has a previous step where we get a playlist item which we can then filter based on title and then we can use the video id to get the video for views).

Once we have gotten videos from each scraper, the master scraper can then sorts the output based on views, creates a final output dictionary and returns that. We then turn that into a JSON for use in the site


# Low Level Design

## Resource


# For my reference

_root = Main root topic
