import argparse
import importlib._bootstrap_external as bootstrap_external
import importlib.util
import logging
import marshal
import types

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from deobfuscator import deobfuscate


def format_code_name(name):
    return name.encode('unicode_escape').decode('ascii')


def parse_code_object(codeObject):
    logger.info('Processing code object %s', format_code_name(codeObject.co_name))
    co_codestring = deobfuscate(codeObject.co_code)
    logger.info('Successfully deobfuscated code object %s', format_code_name(codeObject.co_name))

    logger.info('Collecting constants for code object %s', format_code_name(codeObject.co_name))
    mod_const = []
    for const in codeObject.co_consts:
        if isinstance(const, types.CodeType):
            logger.info(
                'Code object %s contains embedded code object %s',
                format_code_name(codeObject.co_name),
                format_code_name(const.co_name),
            )
            mod_const.append(parse_code_object(const))
        else:
            mod_const.append(const)
    co_constants = tuple(mod_const)

    logger.info('Generating new code object for %s', format_code_name(codeObject.co_name))
    return codeObject.replace(co_code=co_codestring, co_consts=co_constants)


def find_embedded_code_object(codeObject):
    for const in codeObject.co_consts:
        if isinstance(const, types.CodeType):
            return const
        if isinstance(const, (bytes, bytearray)):
            try:
                candidate = marshal.loads(const)
            except (ValueError, EOFError, TypeError):
                continue
            if isinstance(candidate, types.CodeType):
                return candidate
    return None


def unwrap_code_object(codeObject, max_depth=10):
    current = codeObject
    for depth in range(1, max_depth + 1):
        candidate = find_embedded_code_object(current)
        if candidate is None:
            return current
        logger.info('Unwrapped wrapper layer %d: %s', depth, format_code_name(candidate.co_name))
        current = candidate
    logger.warning('Max wrapper unwrap depth (%d) reached.', max_depth)
    return current


def process(ifile, ofile):
    logger.info('Opening file ' + ifile)
    with open(ifile, 'rb') as ifPtr:
        data = ifPtr.read()
    if len(data) < 4:
        raise SystemExit('[!] Header mismatch. The input file is not a valid pyc file.')

    magic = data[:4]
    header_size = getattr(bootstrap_external, 'HEADER_SIZE', 16)
    if magic != importlib.util.MAGIC_NUMBER:
        logger.warning('PYC magic does not match current interpreter, attempting fallback header sizes.')
    candidate_header_sizes = [header_size, 16, 12, 8]

    rootCodeObject = None
    header = None
    for size in candidate_header_sizes:
        if size > len(data):
            continue
        try:
            rootCodeObject = marshal.loads(data[size:])
        except (ValueError, EOFError, TypeError):
            continue
        header = data[:size]
        break

    if rootCodeObject is None:
        max_scan = min(64, len(data))
        for offset in range(0, max_scan):
            try:
                candidate = marshal.loads(data[offset:])
            except (ValueError, EOFError, TypeError):
                continue
            if isinstance(candidate, types.CodeType):
                rootCodeObject = candidate
                header = data[:offset]
                logger.warning('Recovered code object by scanning offset %d.', offset)
                break

    if rootCodeObject is None or header is None:
        raise SystemExit('[!] Header mismatch. The input file is not a valid pyc file.')

    logger.info('Input pyc file header matched')
    logger.debug('Unmarshalling file')
    rootCodeObject = unwrap_code_object(rootCodeObject)
    deob = parse_code_object(rootCodeObject)
    logger.info('Writing deobfuscated code object to disk')
    with open(ofile, 'wb') as ofPtr:
        ofPtr.write(header)
        marshal.dump(deob, ofPtr)
    logger.info('Success')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--ifile', help='Input pyc file name', required=True)
    parser.add_argument('-o', '--ofile', help='Output pyc file name', required=True)
    args = parser.parse_args()
    process(args.ifile, args.ofile)
