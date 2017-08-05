import os

from mock import Mock, MagicMock, call
import pytest

from resumable.core import (
    ResumableFile, ResumableChunk, ResumableSignal, ResumableChunkState
)
from resumable.file import LazyLoadChunkableFile


def test_file(mocker):
    proxy_signals_spy = mocker.spy(ResumableChunk, 'proxy_signals_to')
    register_callback_spy = mocker.spy(ResumableChunk, 'register_callback')

    mock_lazy_load_file = Mock(LazyLoadChunkableFile, chunks=[Mock(), Mock()])

    file = ResumableFile(mock_lazy_load_file)

    assert file.chunks == [ResumableChunk(file, chunk)
                           for chunk in mock_lazy_load_file.chunks]

    proxy_signals_spy.assert_has_calls(
        [call(chunk, file) for chunk in file.chunks]
    )
    register_callback_spy.assert_has_calls(
        [call(chunk, ResumableSignal.CHUNK_COMPLETED,
              file.handle_chunk_completion)
         for chunk in file.chunks]
    )


def test_type(mocker):
    mock_lazy_load_file = MagicMock(LazyLoadChunkableFile, path='file.txt')
    file = ResumableFile(mock_lazy_load_file)
    assert file.type == 'text/plain'


def test_type_unrecognised(mocker):
    mock_lazy_load_file = MagicMock(LazyLoadChunkableFile, path='unknown')
    file = ResumableFile(mock_lazy_load_file)
    assert file.type == ''


def test_query():
    mock_lazy_load_file = Mock(
        LazyLoadChunkableFile,
        path='/dummy/path',
        size=200,
        chunk_size=100,
        chunks=[Mock(), Mock()]
    )
    file = ResumableFile(mock_lazy_load_file)
    assert file.query == {
        'resumableChunkSize': mock_lazy_load_file.chunk_size,
        'resumableTotalSize': mock_lazy_load_file.size,
        'resumableType': file.type,
        'resumableIdentifier': str(file.unique_identifier),
        'resumableFileName': os.path.basename(mock_lazy_load_file.path),
        'resumableRelativePath': mock_lazy_load_file.path,
        'resumableTotalChunks': len(file.chunks)
    }


@pytest.mark.parametrize('chunk_states, completed', [
    ([ResumableChunkState.QUEUED, ResumableChunkState.QUEUED], False),
    ([ResumableChunkState.DONE, ResumableChunkState.QUEUED], False),
    ([ResumableChunkState.DONE, ResumableChunkState.DONE], True),
    ([], True)
])
def test_completed(chunk_states, completed):
    mock_lazy_load_file = Mock(LazyLoadChunkableFile,
                               chunks=[Mock() for _ in chunk_states])
    file = ResumableFile(mock_lazy_load_file)
    for chunk, state in zip(file.chunks, chunk_states):
        chunk.state = state
    assert file.completed == completed


@pytest.mark.parametrize('file_completed', [False, True])
def test_handle_chunk_completion(mocker, file_completed):
    mocker.patch.object(ResumableFile, 'completed', file_completed)

    mock_lazy_load_file = MagicMock(LazyLoadChunkableFile)
    file = ResumableFile(mock_lazy_load_file)
    file.send_signal = MagicMock()

    file.handle_chunk_completion()

    if file_completed:
        file.send_signal.assert_called_once_with(
            ResumableSignal.FILE_COMPLETED
        )
        mock_lazy_load_file.close.assert_called_once()
    else:
        file.send_signal.assert_not_called()
        mock_lazy_load_file.close.assert_not_called()
