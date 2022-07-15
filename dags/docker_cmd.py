def get_dockercmd(params:dict, location):
    """A task which runs in the docker worker and spins up a docker container with the an image and giver parameters.

        Args:
            image(str): contianer image
            stagein_args (list): a list of files necesarry for the executeion
            stageout_args (list): a list of files which are results from the execution
            string_args (str): a string of further arguments which might be needed for the task execution
            entrypoint (str): specify or overwrite the docker entrypoint
            command(str): you can specify or override the command to be executed
            args_to_dockerrun(str): docker options
            
        """
        
    image = params.get('image') # {"image": 'ghcr.io/helmholtz-analytics/heat:1.1.1-alpha'}
    stagein_args = params.get('stagein_args', []) # {"stagein_args": ["demo_knn.py", "iris.h5"]}
    stageout_args = params.get('stageout_args', []) # {"stageout_args": ["result.out"]}
    string_args = params.get('string_args', '')
    entrypoint = params.get('entrypoint', '') # {"entrypoint": "/bin/bash"}
    command = params.get('command', '') # {"command": "python"}
    args_to_dockerrun = params.get('args_to_docker', '')
    
    user_id =  "id -u"
    entrypoint_part = f"--entrypoint={entrypoint}" if entrypoint else ''
    
    working_dir = "/data"
    file_args = stagein_args + stageout_args
    args = " "
    args = args.join(file_args)
    args = args + string_args
    cmd_part = f"-c \"{command} {args}\"" if command else args
    volumes = f"-v {location}:{working_dir} -w={working_dir}" if file_args else ''
    
    cmd = f'userid=$({user_id}) ; docker run {args_to_dockerrun} --user=$userid --rm --name="test" {volumes} {entrypoint_part} {image} {cmd_part}'
    
    return cmd