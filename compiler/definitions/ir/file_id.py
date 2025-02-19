import config
import os

from ir_utils import *
from util import *
import uuid

from definitions.ir.resource import *

## Note: The NULL ident is considered to be the default unknown file id
##
## TODO: WARNING: We have to make sure that a resource in our IR can
## be uniquely determined given a relative or absolute path. Actually,
## we need to make sure that expanding any variable/string in our IR,
## will always return the same result.
##
## WARNING: At the moment it is not clear what resources are saved in
## the Find(self) and in self. This might create problems down the
## road.
##
## TODO: When doing union, I have to really make both file ids point
## to the same file.
class FileId:
    def __init__(self, ident, prefix="", resource=None):
        self.ident = ident
        ## TODO: Add this as part of the resource. Ephemeral resources should
        ##       have a prefix. Normal resources have a file system id. Descriptor
        ##       resources have a number.
        self.prefix = prefix
        ## TODO: Remove all union_find
        ## Initialize the parent
        self.resource=resource

    def __repr__(self):
        if(isinstance(self.resource, EphemeralResource)):
            output = self.get_fifo_suffix()
        else:
            output = "fid:{}:{}".format(self.ident, self.resource)
        return output

    def serialize(self):
        if(isinstance(self.resource, EphemeralResource)):
            output = self.get_fifo_suffix()
        else:
            output = "{}".format(self.resource)
        return output

    def get_fifo_suffix(self):
        fifo_name = "{}#fifo{}".format(self.prefix, self.ident)
        return fifo_name
    ## Serialize as an option for the JSON serialization when sent to
    ## the backend. This is needed as options can either be files or
    ## arguments, and in each case there needs to be a different
    ## serialization procedure.
    def opt_serialize(self):
        return '"{}"'.format(self.serialize())

    ## Returns a shell AST from this file identifier.
    ## TODO: Once the python libdash bindings are done we could use those instead.
    ##
    ## If stdin_dash is True, then we can turn stdin to `-` since the
    ##   context in which we are using it is a command for which `-` means stdin.
    def to_ast(self, stdin_dash=False):
        ## TODO: This here is supposed to identify fifos, but real fifos have a resource
        ##       but are fifos. Therefore eventually we want to have this check correctly
        ##       check if a file id refers to a pipe
        ##
        ## TODO: I am not sure about the FileDescriptor resource
        if(isinstance(self.resource, EphemeralResource)):
            suffix = self.get_fifo_suffix()
            string = os.path.join(config.PASH_TMP_PREFIX, suffix)     
            ## Quote the argument
            argument = [make_kv('Q', string_to_argument(string))]
        elif(isinstance(self.resource, FileDescriptorResource)):
            if (self.resource.is_stdin() and stdin_dash):
                argument = string_to_argument("-")
            else:
                raise NotImplementedError()
        else:
            string = "{}".format(self.resource)
            argument = string_to_argument(string)

        return argument

    def set_resource(self, resource):
        ## The file resource cannot be reset. A pointer can never point to
        ## more than one file resource. However, we can change an ephemeral
        ## resource or a file_descriptor resource.
        assert(not self.has_file_resource())
        self.resource = resource

    def get_resource(self):
        return self.resource

    ## Remove this
    def has_resource(self):
        return (not self.resource is None)

    def has_file_resource(self):
        return (isinstance(self.resource, FileResource))

    def has_file_descriptor_resource(self):
        return (isinstance(self.resource, FileDescriptorResource))

    def is_ephemeral(self):
        return (isinstance(self.resource, EphemeralResource))

    ## Removes a resource from an FID, making it ephemeral
    def make_ephemeral(self):
        self.resource = EphemeralResource()

    def toFileName(self, prefix):
        output = "{}_file{}".format(prefix, self.ident)
        return output

    def isNull(self):
        return self.ident == "NULL"

    def get_ident(self):
        return self.ident
