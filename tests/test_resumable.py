from mock import Mock, call
import pytest

from resumable.core import Resumable
from resumable.util import Config


MOCK_TARGET = 'https://example.com/upload'


@pytest.fixture
def session_mock(mocker):
    return mocker.patch('requests.Session')


@pytest.fixture
def executor_mock(mocker):
    return mocker.patch('resumable.core.ThreadPoolExecutor')


def test_resumable(session_mock, executor_mock):

    mock_sim_uploads = 5
    mock_chunk_size = 100
    mock_headers = {'header': 'foo'}
    mock_max_chunk_retries = 100
    mock_permanent_errors = [500]
    mock_test_chunks = True

    manager = Resumable(MOCK_TARGET, mock_sim_uploads, mock_chunk_size,
                        mock_headers, mock_max_chunk_retries,
                        mock_permanent_errors, mock_test_chunks)

    assert manager.config == Config(
        target=MOCK_TARGET,
        simultaneous_uploads=mock_sim_uploads,
        chunk_size=mock_chunk_size,
        headers=mock_headers,
        max_chunk_retries=mock_max_chunk_retries,
        permanent_errors=mock_permanent_errors,
        test_chunks=mock_test_chunks
    )

    assert manager.session == session_mock.return_value
    manager.session.headers.update.assert_called_once_with(mock_headers)

    assert manager.files == []

    assert manager.executor == executor_mock.return_value
    executor_mock.assert_called_once_with(mock_sim_uploads)


def test_add_file(mocker, session_mock):

    file = Mock(chunks=['foo', 'bar'])
    file_mock = mocker.patch('resumable.core.ResumableFile', return_value=file)
    resolve_chunk_mock = mocker.patch('resumable.core.resolve_chunk')

    mock_path = '/mock/path'
    mock_chunk_size = 100

    manager = Resumable(MOCK_TARGET, chunk_size=mock_chunk_size)
    manager.add_file(mock_path)
    manager.join()

    file_mock.assert_called_once_with(mock_path, mock_chunk_size)
    assert manager.files == [file]

    resolve_chunk_mock.assert_has_calls([
        call(session_mock.return_value, manager.config, file, 'foo'),
        call(session_mock.return_value, manager.config, file, 'bar')
    ])


def test_context_manager():

    manager = Resumable(MOCK_TARGET)
    manager.join = Mock()

    with manager as entered_manager:
        assert entered_manager is manager

    manager.join.assert_called_once()
