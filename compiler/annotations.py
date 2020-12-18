import config
import os
import json
from ir_utils import *
from util import *

##
## Load annotation files
##

def load_annotation_file(abs_annotation_filename):
    with open(abs_annotation_filename) as annotation_file:
        try:
            annotation = json.load(annotation_file)
            return [annotation]
        except json.JSONDecodeError as err:
            log("WARNING: Could not parse annotation for file:", abs_annotation_filename)
            log("|-- {}".format(err))
            return []

def load_annotation_files(annotation_dir):
    annotations = []
    if(not os.path.isabs(annotation_dir)):
        annotation_dir = os.path.join(config.PASH_TOP, annotation_dir)

    for (dirpath, _dirnames, filenames) in os.walk(annotation_dir):
        json_filenames = [os.path.join(dirpath, filename) for filename in filenames
                          if filename.endswith(".json")]
        curr_annotations = [ann for filename in json_filenames for ann in load_annotation_file(filename) ]
        annotations += curr_annotations
    return annotations
    
## TODO: Make the input/output io_list an object and therefore also define
##       methods that transform inputs/outputs <-> args.

## TODO: Think of a way to create a procedure that:
##       - given an annotation
##       - creates two functions:
##         1. One that takes options and creates inputs, outputs for a DFG Node
##         2. One that takes inputs+outputs of a DFG and creates arguments and redirections
##            for the corresponding command.
##
##       Such a procedure would replace the current ad-hoc functions that 
##       re-read the annotation and then do what they are supposed to do.

##
## Inputs, Outputs -> Command Arguments and redirections
##
def construct_args_redirs(command, options, input_fids, output_fids, annotations):
    command_ann = get_command_from_annotations(command, options, annotations)
    assert(not command_ann is None)
    inputs = command_ann['inputs']
    outputs = command_ann['outputs']
    ann_options = []
    if('options' in command_ann):
        ann_options = command_ann['options']
    args, redirs = args_redirs_from_io_list(inputs, input_fids, ann_options, [], [])
    args, redirs = args_redirs_from_io_list(outputs, output_fids, ann_options, args, redirs)
    return args, redirs

def args_redirs_from_io_list(io_list, fids, ann_options, args, redirs):
    rem_fids = fids
    for io in io_list:
        new_args, new_redirs, rem_fids = args_redirs_from_io_list_el(io, rem_fids, ann_options, args, redirs)
        args = new_args
        redirs = new_redirs
    assert(len(rem_fids) == 0)
    return args, redirs

## TODO: We need to handle args[:] followed by stdin by having a look-ahead.
##       It might not be necessary actually. Since it is valid to have them all in
##       args then.
def args_redirs_from_io_list_el(io, fids, ann_options, args, redirs):
    if(io == "stdin"):
        fid = fids[0]
        rem_fids = fids[1:]
        new_redirs = redirs
        new_redirs.append(redir_file_to_stdin(fid.to_ast()))
        return args, new_redirs, rem_fids
    ## TODO: I think that if we have fd redirections that are the same with stdout we don't need to 
    ##       redirect them.
    elif(io == "stdout"):
        fid = fids[0]
        rem_fids = fids[1:]
        new_redirs = redirs
        new_redirs.append(redir_stdout_to_file(fid.to_ast()))
        return args, new_redirs, rem_fids
    else:
        assert(io.startswith("args"))
        indices = io.split("[")[1].split("]")[0]

        if(not ":" in indices):
            index = int(indices)
            ## The argument list is growing with this, so the index might be larger
            args = pad(args, index)
            fid = fids[0]
            rem_fids = fids[1:]
            args[index] = fid
        else:
            start_i_str, end_i_str = indices.split(":")

            start_i = 0
            if(not start_i_str == ""):
                start_i = int(start_i_str)

            ## TODO: We need to handle args[:] followed by stdin by having a look-ahead.
            end_i = len(fids)
            if(not end_i_str == ""):
                end_i = int(end_i_str)

            ## The argument list is growing with this, so the index might be larger
            args = pad(args, end_i - 1)

            ## All the arguments in the required range must be None
            assert(len([arg for arg in args[start_i:end_i] if not arg is None]) == 0)
            for i in range(start_i,end_i):
                args[i] = fids[i-start_i]

            ## Remove the used fids
            rem_fids = fids[(end_i-start_i):]

        ## If the command has the "stdin-hyphen" option turned on,
        ## then it means that `-` should be interpreted as stdin
        ## TODO: What should we do for stdin-hyphen?
        # if('stdin-hyphen' in ann_options):
        #     io_list = [handle_stdin_hyphen(io, options) for io in io_list]
        return args, redirs, rem_fids

## Checks if the annotation for that command exists
def get_command_io_from_annotations(command, options, annotations):
    command_ann = get_command_from_annotations(command, options, annotations)
    if(command_ann):
        inputs = command_ann['inputs']
        outputs = command_ann['outputs']
        ann_options = []
        if('options' in command_ann):
            ann_options = command_ann['options']
        extracted_inputs = interpret_io_list(inputs, options, ann_options)
        extracted_outputs = interpret_io_list(outputs, options, ann_options)
        option_indices = rest_options(extracted_inputs, extracted_outputs, options)
        return (extracted_inputs, extracted_outputs, option_indices)

def rest_options(inputs, outputs, options):
    input_output_indices = [io[1] for io in inputs + outputs
                            if isinstance(io, tuple)]
    io_indices_set = set(input_output_indices)
    all_indices = [("option", i) for i in range(len(options))
                   if not i in io_indices_set]
    return all_indices

def interpret_io_list(files, options, ann_options):
    io_files = []
    for io in files:
        io_files += interpret_io(io, options, ann_options)
    return io_files

def interpret_io(io, options, ann_options):
    if(io == "stdin"):
        return ["stdin"]
    elif(io == "stdout"):
        return ["stdout"]
    else:
        assert(io.startswith("args"))
        indices = io.split("[")[1].split("]")[0]

        # log(io, options)

        ## Find the file arguments (and their indices)
        args_indices = non_option_args_indices(options)

        ## Single index
        if(not ":" in indices):
            index = int(indices)
            io_list = [("option", args_indices[index][1])]
        else:
            start_i_str, end_i_str = indices.split(":")

            start_i = 0
            if(not start_i_str == ""):
                start_i = int(start_i_str)

            end_i = len(args_indices)
            if(not end_i_str == ""):
                end_i = int(end_i_str)

            io_list = []
            for _, i in args_indices[start_i:end_i]:
                io_list.append(("option", i))

        ## If the command has the "stdin-hyphen" option turned on,
        ## then it means that `-` should be interpreted as stdin
        if('stdin-hyphen' in ann_options):
            io_list = [handle_stdin_hyphen(io, options) for io in io_list]
        return io_list

def handle_stdin_hyphen(io, options):
    if(isinstance(io, tuple)):
        option = options[io[1]]

        ## TODO: For absolute completeness, not being able to
        ## interpret the argument to `-` means that it should also
        ## bump up the command class (or not be translated to the DFG).
        if(format_arg_chars(option) == '-'):
            return "stdin"
    return io

def get_command_class_from_annotations(command, options, annotations):
    command_ann = get_command_from_annotations(command, options, annotations)
    if(command_ann):
        return command_ann['class']

def get_command_from_annotations(command, options, annotations):
    ## Find an annotation for this command
    relevant_annotations = [ann for ann in annotations if ann['command'] == command]
    if(len(relevant_annotations) == 0):
        return None
    elif(len(relevant_annotations) > 1):
        log("Warning: More than one annotation for command:", command)

    return get_command_from_annotation(command, options, relevant_annotations[0])

def get_command_from_annotation(command, options, annotation):
    assert(annotation['command'] == command)

    cases = annotation['cases']
    case = find_annotation_case(options, cases)
    return case

def find_annotation_case(options, cases):
    for case in cases:
        if(predicate_satisfied(options, case['predicate'])):
            return case

    ## Unreachable
    assert(False)

def predicate_satisfied(options, predicate):
    if(predicate == 'default'):
        return True

    func = interpret_predicate(predicate)
    return func(options)

def interpret_predicate(predicate):
    # log(predicate)
    operator = predicate['operator']
    operands = []
    try:
        operands = predicate['operands']
    except:
        pass
    if(operator == 'len_args_eq'):
        return lambda options: len_args(operands[0], options)
    elif(operator == 'exists'):
        return lambda options: exists_operator(operands, options)
    elif(operator == 'value'):
        return lambda options: value_operator(operands, options)
    elif(operator == 'all'):
        return lambda options: all_operator(operands, options)
    elif(operator == 'or'):
        return lambda options: or_operator(operands, options)
    elif(operator == 'not'):
        return lambda options: not_operator(operands, options)

    ## TODO: Fill in the rest
    return lambda x: log("Uninterpreted operator:", operator); False


##
## Helper functions for predicate interpretation
##

def len_args(desired_length, options):
    args = non_option_args(options)
    return (len(args) == desired_length)

def exists_operator(desired_options, options):
    opt_args_set = set(option_args(options))
    existence = map(lambda opt: opt in opt_args_set, desired_options)
    return any(existence)

## Checks that an option exists and that it has a specific value
def value_operator(option_value, options):
    args_list = format_args(options)
    desired_opt = option_value[0]
    desired_val = option_value[1]
    ## If the desired option does exist, and the next argument is indeed the correct value
    try:
        opt_i = args_list.index(desired_opt)
        val = args_list[opt_i+1]
        return (desired_val == val)
    except:
        return False

def all_operator(desired_options, options):
    opt_args_set = set(option_args(options))
    existence = map(lambda opt: opt in opt_args_set, desired_options)
    return all(existence)

def or_operator(operands, options):
    operand_predicates = map(lambda op: interpret_predicate(op)(options), operands)
    return any(operand_predicates)

## Operands: One predicate
def not_operator(operands, options):
    assert(len(operands) == 1)
    operand = operands[0]
    return not interpret_predicate(operand)(options)

